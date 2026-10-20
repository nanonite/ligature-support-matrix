// C++ oracle driver for the crypto-mixed pilot (Stage 8B, chainlink #48).
//
// Command-line contract (oracle-PROTOCOL.md section 5):
//
//     oracle_driver <cases.jsonl> <results.jsonl>
//
// Reads the UTF-8 JSONL case file, validates every case against the
// operation contract in oracle/operations.md, executes each comparable case
// against the pinned Botan 3.13.0 checkout (commit
// 2a81eef56c96c237e590c27f9a75e60317c9c700, minimized scalar build from
// oracle/build_upstream.sh), and writes exactly one result object per case to
// the output file in ascending bytewise case_id order. Diagnostics go to
// stderr; the result stream is always valid JSONL.
//
// Exit codes: 0 success; 1 usage/IO failure; 2 case-file validation failure
// (malformed JSON, unknown field, duplicate case_id, out-of-domain input);
// 3 an upstream exception outside the operation's error taxonomy.
//
// The driver links only the Botan library and the C++ standard library; JSON
// parsing is the strict minimal parser below (adapted from the date-creusot
// driver) so the driver has no third-party dependencies.

#include <algorithm>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include <botan/aead.h>
#include <botan/exceptn.h>
#include <botan/mac.h>
#include <botan/stream_cipher.h>

// ---------------------------------------------------------------------------
// Minimal strict JSON parser (objects, arrays, strings, integers, literals).
// Case inputs never contain fractions or exponents, so those are rejected.
// ---------------------------------------------------------------------------

struct JsonValue {
    enum Type { Null, Bool, Int, String, Object, Array };

    Type type = Null;
    bool bool_value = false;
    long long int_value = 0;
    std::string string_value;
    // Object members as parallel vectors: std::pair<std::string, JsonValue>
    // would need JsonValue complete inside its own definition.
    std::vector<std::string> object_keys;
    std::vector<JsonValue> object_values;
    std::vector<JsonValue> array_value;

    const JsonValue* find(const std::string& key) const {
        if (type != Object) {
            return nullptr;
        }
        for (std::size_t i = 0; i < object_keys.size(); ++i) {
            if (object_keys[i] == key) {
                return &object_values[i];
            }
        }
        return nullptr;
    }
};

class JsonParser {
public:
    explicit JsonParser(const std::string& text) : text_(text) {}

    JsonValue parse() {
        JsonValue value = parse_value();
        skip_ws();
        if (pos_ != text_.size()) {
            fail("trailing characters after JSON value");
        }
        return value;
    }

private:
    const std::string& text_;
    std::size_t pos_ = 0;

    [[noreturn]] void fail(const std::string& message) const {
        throw std::runtime_error("JSON parse error at byte " + std::to_string(pos_) +
                                 ": " + message);
    }

    void skip_ws() {
        while (pos_ < text_.size() &&
               (text_[pos_] == ' ' || text_[pos_] == '\t' ||
                text_[pos_] == '\n' || text_[pos_] == '\r')) {
            ++pos_;
        }
    }

    char peek() const {
        if (pos_ >= text_.size()) {
            throw std::runtime_error("unexpected end of input");
        }
        return text_[pos_];
    }

    void expect(char c) {
        if (peek() != c) {
            fail(std::string("expected '") + c + "'");
        }
        ++pos_;
    }

    JsonValue parse_value() {
        skip_ws();
        switch (peek()) {
            case '{': return parse_object();
            case '[': return parse_array();
            case '"': {
                JsonValue value;
                value.type = JsonValue::String;
                value.string_value = parse_string();
                return value;
            }
            case 't': expect_literal("true"); {
                JsonValue value;
                value.type = JsonValue::Bool;
                value.bool_value = true;
                return value;
            }
            case 'f': expect_literal("false"); {
                JsonValue value;
                value.type = JsonValue::Bool;
                value.bool_value = false;
                return value;
            }
            case 'n': expect_literal("null"); return JsonValue{};
            default: return parse_number();
        }
    }

    void expect_literal(const char* literal) {
        for (const char* p = literal; *p != '\0'; ++p) {
            if (pos_ >= text_.size() || text_[pos_] != *p) {
                fail(std::string("invalid literal, expected '") + literal + "'");
            }
            ++pos_;
        }
    }

    JsonValue parse_object() {
        JsonValue value;
        value.type = JsonValue::Object;
        expect('{');
        skip_ws();
        if (peek() == '}') {
            ++pos_;
            return value;
        }
        while (true) {
            skip_ws();
            std::string key = parse_string();
            if (value.find(key) != nullptr) {
                fail("duplicate object key '" + key + "'");
            }
            skip_ws();
            expect(':');
            JsonValue member = parse_value();
            value.object_keys.push_back(std::move(key));
            value.object_values.push_back(std::move(member));
            skip_ws();
            char c = peek();
            if (c == ',') {
                ++pos_;
                continue;
            }
            if (c == '}') {
                ++pos_;
                return value;
            }
            fail("expected ',' or '}' in object");
        }
    }

    JsonValue parse_array() {
        JsonValue value;
        value.type = JsonValue::Array;
        expect('[');
        skip_ws();
        if (peek() == ']') {
            ++pos_;
            return value;
        }
        while (true) {
            value.array_value.push_back(parse_value());
            skip_ws();
            char c = peek();
            if (c == ',') {
                ++pos_;
                continue;
            }
            if (c == ']') {
                ++pos_;
                return value;
            }
            fail("expected ',' or ']' in array");
        }
    }

    std::string parse_string() {
        expect('"');
        std::string result;
        while (true) {
            if (pos_ >= text_.size()) {
                fail("unterminated string");
            }
            char c = text_[pos_++];
            if (c == '"') {
                return result;
            }
            if (static_cast<unsigned char>(c) < 0x20) {
                fail("unescaped control character in string");
            }
            if (c != '\\') {
                result.push_back(c);
                continue;
            }
            if (pos_ >= text_.size()) {
                fail("unterminated escape");
            }
            char esc = text_[pos_++];
            switch (esc) {
                case '"': result.push_back('"'); break;
                case '\\': result.push_back('\\'); break;
                case '/': result.push_back('/'); break;
                case 'b': result.push_back('\b'); break;
                case 'f': result.push_back('\f'); break;
                case 'n': result.push_back('\n'); break;
                case 'r': result.push_back('\r'); break;
                case 't': result.push_back('\t'); break;
                case 'u': {
                    if (pos_ + 4 > text_.size()) {
                        fail("truncated \\u escape");
                    }
                    unsigned code = 0;
                    for (int i = 0; i < 4; ++i) {
                        char h = text_[pos_++];
                        code <<= 4;
                        if (h >= '0' && h <= '9') code |= static_cast<unsigned>(h - '0');
                        else if (h >= 'a' && h <= 'f') code |= static_cast<unsigned>(h - 'a' + 10);
                        else if (h >= 'A' && h <= 'F') code |= static_cast<unsigned>(h - 'A' + 10);
                        else fail("invalid hex digit in \\u escape");
                    }
                    // Case files in this pilot are ASCII; reject anything else.
                    if (code > 0x7F) {
                        fail("non-ASCII \\u escape in case input");
                    }
                    result.push_back(static_cast<char>(code));
                    break;
                }
                default: fail("invalid escape character");
            }
        }
    }

    JsonValue parse_number() {
        std::size_t start = pos_;
        if (pos_ < text_.size() && text_[pos_] == '-') {
            ++pos_;
        }
        if (pos_ >= text_.size() || !std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
            fail("invalid number");
        }
        if (text_[pos_] == '0') {
            ++pos_;
        } else {
            while (pos_ < text_.size() &&
                   std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        }
        if (pos_ < text_.size() &&
            (text_[pos_] == '.' || text_[pos_] == 'e' || text_[pos_] == 'E')) {
            fail("non-integer number in case input");
        }
        std::string token = text_.substr(start, pos_ - start);
        JsonValue value;
        try {
            value.int_value = std::stoll(token);
        } catch (const std::exception&) {
            fail("integer out of range: " + token);
        }
        value.type = JsonValue::Int;
        return value;
    }
};

// ---------------------------------------------------------------------------
// Case model and validation (oracle/operations.md)
// ---------------------------------------------------------------------------

using Bytes = std::vector<uint8_t>;

constexpr long long kKeystreamCap = 1LL << 38;   // 2^32 blocks of 64 bytes
constexpr long long kMaxLengthQuery = 1LL << 62;
constexpr long long kMaxWrite = 1LL << 20;

class CaseError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};

struct Case {
    std::string case_id;
    std::string op;
    JsonValue inputs;
    bool excluded = false;
};

enum class Field { Hex, Key, Nonce, Int, Direction, HexArray, IntArray };

struct FieldSpec {
    const char* name;
    Field kind;
};

const std::vector<std::pair<std::string, std::vector<FieldSpec>>>& operation_specs() {
    static const std::vector<std::pair<std::string, std::vector<FieldSpec>>> specs = {
        {"aead_encrypt", {{"key", Field::Key}, {"nonce", Field::Nonce}, {"ad", Field::Hex}, {"plaintext", Field::Hex}}},
        {"aead_decrypt", {{"key", Field::Key}, {"nonce", Field::Nonce}, {"ad", Field::Hex}, {"ciphertext", Field::Hex}}},
        {"aead_output_length", {{"direction", Field::Direction}, {"input_length", Field::Int}}},
        {"chacha20_xor", {{"key", Field::Key}, {"nonce", Field::Nonce}, {"seek", Field::Int}, {"input", Field::Hex}}},
        {"chacha20_remaining", {{"key", Field::Key}, {"nonce", Field::Nonce}, {"seek", Field::Int}, {"writes", Field::IntArray}}},
        {"poly1305_mac", {{"key", Field::Key}, {"message", Field::Hex}}},
        {"poly1305_mac_pieces", {{"key", Field::Key}, {"pieces", Field::HexArray}}},
        {"poly1305_mac_split", {{"key", Field::Key}, {"message", Field::Hex}, {"split", Field::Int}}},
        {"poly1305_update_unkeyed", {{"message", Field::Hex}}},
        {"poly1305_update_after_final", {{"key", Field::Key}, {"first", Field::Hex}, {"second", Field::Hex}}},
    };
    return specs;
}

const std::vector<FieldSpec>* find_spec(const std::string& op) {
    for (const auto& entry : operation_specs()) {
        if (entry.first == op) {
            return &entry.second;
        }
    }
    return nullptr;
}

Bytes decode_hex(const std::string& text, const std::string& field) {
    if (text.size() % 2 != 0) {
        throw CaseError("field '" + field + "' has odd-length hex");
    }
    Bytes out;
    out.reserve(text.size() / 2);
    auto nibble = [&](char c) -> uint8_t {
        if (c >= '0' && c <= '9') return static_cast<uint8_t>(c - '0');
        if (c >= 'a' && c <= 'f') return static_cast<uint8_t>(c - 'a' + 10);
        throw CaseError("field '" + field + "' is not lower-case hex");
    };
    for (std::size_t i = 0; i < text.size(); i += 2) {
        out.push_back(static_cast<uint8_t>((nibble(text[i]) << 4) | nibble(text[i + 1])));
    }
    return out;
}

void validate_field(const FieldSpec& spec, const JsonValue& value) {
    const std::string name = spec.name;
    switch (spec.kind) {
        case Field::Hex:
        case Field::Key:
        case Field::Nonce: {
            if (value.type != JsonValue::String) {
                throw CaseError("field '" + name + "' must be a hex string");
            }
            const Bytes bytes = decode_hex(value.string_value, name);
            if (spec.kind == Field::Key && bytes.size() != 32) {
                throw CaseError("field '" + name + "' must be 32 bytes");
            }
            if (spec.kind == Field::Nonce && bytes.size() != 12) {
                throw CaseError("field '" + name + "' must be 12 bytes");
            }
            return;
        }
        case Field::Int:
            if (value.type != JsonValue::Int || value.int_value < 0) {
                throw CaseError("field '" + name + "' must be a non-negative integer");
            }
            return;
        case Field::Direction:
            if (value.type != JsonValue::String ||
                (value.string_value != "encrypt" && value.string_value != "decrypt")) {
                throw CaseError("field '" + name + "' must be \"encrypt\" or \"decrypt\"");
            }
            return;
        case Field::HexArray:
            if (value.type != JsonValue::Array) {
                throw CaseError("field '" + name + "' must be an array of hex strings");
            }
            for (const auto& item : value.array_value) {
                if (item.type != JsonValue::String) {
                    throw CaseError("field '" + name + "' must be an array of hex strings");
                }
                decode_hex(item.string_value, name);
            }
            return;
        case Field::IntArray:
            if (value.type != JsonValue::Array) {
                throw CaseError("field '" + name + "' must be an array of integers");
            }
            for (const auto& item : value.array_value) {
                if (item.type != JsonValue::Int || item.int_value < 0 || item.int_value > kMaxWrite) {
                    throw CaseError("field '" + name + "' entries must be integers in [0, 2^20]");
                }
            }
            return;
    }
}

const JsonValue& input(const Case& c, const char* name) {
    const JsonValue* value = c.inputs.find(name);
    if (value == nullptr) {
        throw CaseError("missing input '" + std::string(name) + "'");
    }
    return *value;
}

Bytes hex_input(const Case& c, const char* name) {
    return decode_hex(input(c, name).string_value, name);
}

long long int_input(const Case& c, const char* name) {
    return input(c, name).int_value;
}

void validate_domain(const Case& c) {
    if (c.op == "aead_output_length" && int_input(c, "input_length") > kMaxLengthQuery) {
        throw CaseError("input_length must be at most 2^62");
    }
    if (c.op == "chacha20_xor" || c.op == "chacha20_remaining") {
        if (int_input(c, "seek") >= kKeystreamCap) {
            throw CaseError("seek must be below 2^38");
        }
    }
    if (c.op == "chacha20_xor" && hex_input(c, "input").size() > static_cast<std::size_t>(kMaxWrite)) {
        throw CaseError("input must be at most 2^20 bytes");
    }
    if (c.op == "poly1305_mac_split" &&
        static_cast<std::size_t>(int_input(c, "split")) > hex_input(c, "message").size()) {
        throw CaseError("split must not exceed the message length");
    }
}

bool valid_case_id(const std::string& id) {
    if (id.empty()) {
        return false;
    }
    return std::all_of(id.begin(), id.end(), [](char ch) {
        return (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '-';
    });
}

Case parse_case(const JsonValue& root) {
    if (root.type != JsonValue::Object) {
        throw CaseError("case is not a JSON object");
    }
    for (const std::string& key : root.object_keys) {
        if (key != "case_id" && key != "op" && key != "inputs" &&
            key != "oracle_scope" && key != "exclusion_reason") {
            throw CaseError("unknown case field '" + key + "'");
        }
    }
    Case c;
    const JsonValue* id = root.find("case_id");
    if (id == nullptr || id->type != JsonValue::String || !valid_case_id(id->string_value)) {
        throw CaseError("case_id must be a non-empty [a-z0-9-] string");
    }
    c.case_id = id->string_value;
    const JsonValue* op = root.find("op");
    if (op == nullptr || op->type != JsonValue::String) {
        throw CaseError("op must be a string");
    }
    c.op = op->string_value;
    const std::vector<FieldSpec>* spec = find_spec(c.op);
    if (spec == nullptr) {
        throw CaseError("unknown op '" + c.op + "'");
    }
    const JsonValue* inputs = root.find("inputs");
    if (inputs == nullptr || inputs->type != JsonValue::Object) {
        throw CaseError("inputs must be an object");
    }
    c.inputs = *inputs;
    if (c.inputs.object_keys.size() != spec->size()) {
        throw CaseError("inputs for '" + c.op + "' have the wrong field set");
    }
    for (const auto& field : *spec) {
        const JsonValue* value = c.inputs.find(field.name);
        if (value == nullptr) {
            throw CaseError("missing input '" + std::string(field.name) + "'");
        }
        validate_field(field, *value);
    }
    const JsonValue* scope = root.find("oracle_scope");
    const JsonValue* reason = root.find("exclusion_reason");
    if (scope != nullptr) {
        if (scope->type != JsonValue::String ||
            (scope->string_value != "compare" && scope->string_value != "excluded")) {
            throw CaseError("oracle_scope must be \"compare\" or \"excluded\"");
        }
        c.excluded = scope->string_value == "excluded";
    }
    if (c.excluded) {
        if (reason == nullptr || reason->type != JsonValue::String || reason->string_value.empty()) {
            throw CaseError("excluded case needs a non-empty exclusion_reason");
        }
    } else if (reason != nullptr) {
        throw CaseError("exclusion_reason is forbidden for a compare case");
    }
    validate_domain(c);
    return c;
}

// ---------------------------------------------------------------------------
// Operations against the pinned Botan build
// ---------------------------------------------------------------------------

struct Outcome {
    bool ok = true;
    std::string err_kind;
    std::string value_json;
};

Outcome ok_bytes(const uint8_t* data, std::size_t size) {
    static const char digits[] = "0123456789abcdef";
    std::string hex;
    hex.reserve(size * 2);
    for (std::size_t i = 0; i < size; ++i) {
        hex.push_back(digits[data[i] >> 4]);
        hex.push_back(digits[data[i] & 0x0F]);
    }
    return {true, "", "{\"type\":\"bytes\",\"encoding\":\"hex\",\"value\":\"" + hex + "\"}"};
}

template <typename Container>
Outcome ok_bytes(const Container& bytes) {
    return ok_bytes(bytes.data(), bytes.size());
}

Outcome ok_int(uint64_t value) {
    return {true, "", std::to_string(value)};
}

Outcome err(const std::string& kind) {
    return {false, kind, ""};
}

std::unique_ptr<Botan::StreamCipher> keyed_chacha(const Case& c) {
    auto cipher = Botan::StreamCipher::create_or_throw("ChaCha(20)");
    cipher->set_key(hex_input(c, "key"));
    const Bytes nonce = hex_input(c, "nonce");
    cipher->set_iv(nonce.data(), nonce.size());
    cipher->seek(static_cast<uint64_t>(int_input(c, "seek")));
    return cipher;
}

std::unique_ptr<Botan::MessageAuthenticationCode> poly1305() {
    return Botan::MessageAuthenticationCode::create_or_throw("Poly1305");
}

Outcome run_case(const Case& c) {
    if (c.op == "aead_encrypt") {
        auto mode = Botan::AEAD_Mode::create_or_throw("ChaCha20Poly1305", Botan::Cipher_Dir::Encryption);
        mode->set_key(hex_input(c, "key"));
        mode->set_associated_data(hex_input(c, "ad"));
        mode->start(hex_input(c, "nonce"));
        const Bytes plaintext = hex_input(c, "plaintext");
        Botan::secure_vector<uint8_t> buf(plaintext.begin(), plaintext.end());
        try {
            mode->finish(buf);
        } catch (const Botan::Invalid_State&) {
            return err("message_too_long");
        }
        return ok_bytes(buf);
    }
    if (c.op == "aead_decrypt") {
        auto mode = Botan::AEAD_Mode::create_or_throw("ChaCha20Poly1305", Botan::Cipher_Dir::Decryption);
        mode->set_key(hex_input(c, "key"));
        mode->set_associated_data(hex_input(c, "ad"));
        mode->start(hex_input(c, "nonce"));
        const Bytes ciphertext = hex_input(c, "ciphertext");
        Botan::secure_vector<uint8_t> buf(ciphertext.begin(), ciphertext.end());
        try {
            mode->finish(buf);
        } catch (const Botan::Invalid_Authentication_Tag&) {
            return err("authentication_failed");
        } catch (const Botan::Invalid_Argument&) {
            return err("ciphertext_too_short");
        } catch (const Botan::Invalid_State&) {
            return err("message_too_long");
        }
        return ok_bytes(buf);
    }
    if (c.op == "aead_output_length") {
        const bool encrypt = input(c, "direction").string_value == "encrypt";
        auto mode = Botan::AEAD_Mode::create_or_throw(
            "ChaCha20Poly1305", encrypt ? Botan::Cipher_Dir::Encryption : Botan::Cipher_Dir::Decryption);
        const auto length = static_cast<std::size_t>(int_input(c, "input_length"));
        try {
            return ok_int(mode->output_length(length));
        } catch (const Botan::Invalid_Argument&) {
            return err("ciphertext_too_short");
        } catch (const Botan::Invalid_State&) {
            return err("message_too_long");
        }
    }
    if (c.op == "chacha20_xor") {
        auto cipher = keyed_chacha(c);
        Bytes buf = hex_input(c, "input");
        try {
            cipher->encrypt(buf);
        } catch (const Botan::Invalid_State&) {
            return err("keystream_exhausted");
        }
        return ok_bytes(buf);
    }
    if (c.op == "chacha20_remaining") {
        auto cipher = keyed_chacha(c);
        for (const auto& write : input(c, "writes").array_value) {
            Bytes buf(static_cast<std::size_t>(write.int_value));
            try {
                cipher->write_keystream(buf);
            } catch (const Botan::Invalid_State&) {
                return err("keystream_exhausted");
            }
        }
        const std::optional<uint64_t> remaining = cipher->remaining_keystream_bytes();
        if (!remaining.has_value()) {
            throw std::runtime_error("ChaCha(20) with a 96-bit nonce reported no keystream cap");
        }
        return ok_int(*remaining);
    }
    if (c.op == "poly1305_mac") {
        auto mac = poly1305();
        mac->set_key(hex_input(c, "key"));
        mac->update(hex_input(c, "message"));
        return ok_bytes(mac->final());
    }
    if (c.op == "poly1305_mac_pieces") {
        auto mac = poly1305();
        mac->set_key(hex_input(c, "key"));
        for (const auto& piece : input(c, "pieces").array_value) {
            mac->update(decode_hex(piece.string_value, "pieces"));
        }
        return ok_bytes(mac->final());
    }
    if (c.op == "poly1305_mac_split") {
        auto mac = poly1305();
        mac->set_key(hex_input(c, "key"));
        const Bytes message = hex_input(c, "message");
        const auto split = static_cast<std::size_t>(int_input(c, "split"));
        mac->update(message.data(), split);
        mac->update(message.data() + split, message.size() - split);
        return ok_bytes(mac->final());
    }
    if (c.op == "poly1305_update_unkeyed") {
        auto mac = poly1305();
        try {
            mac->update(hex_input(c, "message"));
        } catch (const Botan::Invalid_State&) {
            return err("key_not_set");
        }
        return {true, "", "\"accepted\""};
    }
    if (c.op == "poly1305_update_after_final") {
        auto mac = poly1305();
        mac->set_key(hex_input(c, "key"));
        mac->update(hex_input(c, "first"));
        (void)mac->final();
        try {
            mac->update(hex_input(c, "second"));
        } catch (const Botan::Invalid_State&) {
            return err("key_not_set");
        }
        return {true, "", "\"accepted\""};
    }
    throw std::runtime_error("unhandled op '" + c.op + "'");
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: oracle_driver <cases.jsonl> <results.jsonl>\n";
        return 1;
    }
    std::ifstream in(argv[1], std::ios::binary);
    if (!in) {
        std::cerr << "cannot open case file " << argv[1] << "\n";
        return 1;
    }

    std::vector<Case> cases;
    std::set<std::string> seen;
    std::string line;
    std::size_t line_number = 0;
    while (std::getline(in, line)) {
        ++line_number;
        try {
            if (!line.empty() && line.back() == '\r') {
                throw CaseError("CRLF line ending");
            }
            if (line.empty()) {
                throw CaseError("empty line");
            }
            JsonParser parser(line);
            Case c = parse_case(parser.parse());
            if (!seen.insert(c.case_id).second) {
                throw CaseError("duplicate case_id '" + c.case_id + "'");
            }
            cases.push_back(std::move(c));
        } catch (const std::exception& e) {
            std::cerr << argv[1] << ":" << line_number << ": " << e.what() << "\n";
            return 2;
        }
    }
    if (in.bad()) {
        std::cerr << "error reading " << argv[1] << "\n";
        return 1;
    }

    std::sort(cases.begin(), cases.end(),
              [](const Case& a, const Case& b) { return a.case_id < b.case_id; });

    std::vector<std::string> results;
    results.reserve(cases.size());
    for (const Case& c : cases) {
        std::string record = "{\"case_id\":\"" + c.case_id + "\",\"status\":";
        if (c.excluded) {
            record += "\"ok\",\"value\":null}";
            results.push_back(record);
            continue;
        }
        try {
            const Outcome outcome = run_case(c);
            if (outcome.ok) {
                record += "\"ok\",\"value\":" + outcome.value_json + "}";
            } else {
                record += "\"err\",\"err_kind\":\"" + outcome.err_kind + "\"}";
            }
        } catch (const std::exception& e) {
            std::cerr << c.case_id << ": upstream exception outside the error taxonomy: "
                      << e.what() << "\n";
            return 3;
        }
        results.push_back(record);
    }

    std::ofstream out(argv[2], std::ios::binary | std::ios::trunc);
    if (!out) {
        std::cerr << "cannot open result file " << argv[2] << "\n";
        return 1;
    }
    for (const auto& record : results) {
        out << record << '\n';
    }
    out.flush();
    if (!out) {
        std::cerr << "error writing " << argv[2] << "\n";
        return 1;
    }
    return 0;
}
