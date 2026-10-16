// C++ oracle driver for the date-creusot pilot (Stage 8B).
//
// Command-line contract (oracle-PROTOCOL.md section 5):
//
//     oracle_driver <cases.jsonl> <results.jsonl>
//
// Reads the UTF-8 JSONL case file, validates every case against the
// operation contract (oracle/operations.md), executes each comparable case
// against the pinned upstream HowardHinnant/date checkout (v3.0.5,
// commit 179a6b921ccd6179b5b04dce812a89f71a51b4df), and writes exactly one
// result object per case to the output file in ascending bytewise case_id
// order. Diagnostics go to stderr; the result stream is always valid JSONL.
//
// Exit codes: 0 success; 1 usage/IO failure; 2 case-file validation failure
// (malformed JSON, unknown field, duplicate case_id, out-of-domain input).
//
// Operations (see oracle/operations.md for the full contract):
//   days_from_civil:        {y, m, d} -> i32 epoch day count
//   civil_from_days:        {z}       -> {y, m, d}
//   weekday_from_days:      {z}       -> u8 (0=Sunday .. 6=Saturday)
//   ymd_ok:                 {y, m, d} -> bool
//   iso_weekday_from_days:  {z}       -> u8 (1=Monday .. 7=Sunday)
//
// The driver links only the pinned upstream headers and the C++ standard
// library; JSON parsing is the strict minimal parser below so the driver
// has no third-party dependencies.

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

#include "date/date.h"
#include "date/iso_week.h"

// ---------------------------------------------------------------------------
// Minimal strict JSON parser (objects, arrays, strings, numbers, literals).
// Numbers are kept both as the raw token and as a long long when the token
// is an integer literal; input fields must be integer literals.
// ---------------------------------------------------------------------------

struct JsonValue {
    enum Type { Null, Bool, Int, String, Object, Array };

    Type type = Null;
    bool bool_value = false;
    long long int_value = 0;
    std::string string_value;
    std::vector<std::pair<std::string, JsonValue>> object_value;
    std::vector<JsonValue> array_value;

    const JsonValue* find(const std::string& key) const {
        if (type != Object) {
            return nullptr;
        }
        for (const auto& member : object_value) {
            if (member.first == key) {
                return &member.second;
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
            skip_ws();
            expect(':');
            JsonValue member = parse_value();
            value.object_value.emplace_back(std::move(key), std::move(member));
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
                    // Surrogate pair handling: case IDs in this pilot are
                    // ASCII, so reject non-ASCII code points outright.
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
        bool fractional = false;
        if (pos_ < text_.size() && text_[pos_] == '.') {
            fractional = true;
            ++pos_;
            if (pos_ >= text_.size() ||
                !std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                fail("invalid number: missing digits after '.'");
            }
            while (pos_ < text_.size() &&
                   std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        }
        if (pos_ < text_.size() && (text_[pos_] == 'e' || text_[pos_] == 'E')) {
            fractional = true;
            ++pos_;
            if (pos_ < text_.size() && (text_[pos_] == '+' || text_[pos_] == '-')) {
                ++pos_;
            }
            if (pos_ >= text_.size() ||
                !std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                fail("invalid number: missing exponent digits");
            }
            while (pos_ < text_.size() &&
                   std::isdigit(static_cast<unsigned char>(text_[pos_]))) {
                ++pos_;
            }
        }
        std::string token = text_.substr(start, pos_ - start);
        JsonValue value;
        if (fractional) {
            // Input fields must be integer literals; a fraction or exponent
            // in an input position is a case-contract violation.
            value.type = JsonValue::String; // marker: non-integer number
            value.string_value = token;
            return value;
        }
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
// Case model and validation
// ---------------------------------------------------------------------------

struct Case {
    std::string case_id;
    std::string op;
    std::string scope = "compare";
    std::string exclusion_reason;
    long long y = 0;
    long long m = 0;
    long long d = 0;
    long long z = 0;
};

// Domain limits from the operation contract (oracle/operations.md).
// The year newtype holds i16; month/day newtypes hold u8; the epoch day
// count newtype holds i32. civil_from_days is only defined (no signed
// overflow in the C++ era decomposition) over the range to_days produces
// for years [-32767, 32767].
constexpr long long kYearMin = -32768;                 // i16::MIN, ok() == false
constexpr long long kYearMax = 32767;                  // i16::MAX
constexpr long long kMonthMin = 0;                     // u8 domain
constexpr long long kMonthMax = 255;
constexpr long long kDayMin = 0;                       // u8 domain
constexpr long long kDayMax = 255;
constexpr long long kZMin = -12687428;                 // to_days(-32767-01-01)
constexpr long long kZMax = 11248737;                  // to_days(32767-12-31)
constexpr long long kI32Min = -2147483648LL - 1;       // INT32_MIN
constexpr long long kI32Max = 2147483647;              // INT32_MAX

bool in_range(long long value, long long low, long long high) {
    return value >= low && value <= high;
}

long long require_int(const JsonValue& case_object, const std::string& key) {
    const JsonValue* field = case_object.find(key);
    if (field == nullptr) {
        throw std::runtime_error("missing input field: " + key);
    }
    if (field->type != JsonValue::Int) {
        throw std::runtime_error("input field must be an integer literal: " + key);
    }
    return field->int_value;
}

void require_exactly(const JsonValue& inputs, const std::vector<std::string>& expected) {
    if (inputs.type != JsonValue::Object) {
        throw std::runtime_error("inputs must be a JSON object");
    }
    std::set<std::string> declared(expected.begin(), expected.end());
    for (const auto& member : inputs.object_value) {
        if (declared.count(member.first) == 0) {
            throw std::runtime_error("unknown input field: " + member.first);
        }
    }
    for (const std::string& key : expected) {
        if (inputs.find(key) == nullptr) {
            throw std::runtime_error("missing input field: " + key);
        }
    }
}

Case parse_case(const std::string& line, int line_number) {
    JsonParser parser(line);
    JsonValue root = parser.parse();
    if (root.type != JsonValue::Object) {
        throw std::runtime_error("case must be a JSON object");
    }

    // Top-level fields: case_id, op, inputs are required; oracle_scope and
    // exclusion_reason are the only allowed metadata fields.
    for (const auto& member : root.object_value) {
        const std::string& key = member.first;
        if (key != "case_id" && key != "op" && key != "inputs" &&
            key != "oracle_scope" && key != "exclusion_reason") {
            throw std::runtime_error("unknown case field: " + key);
        }
    }

    Case item;
    const JsonValue* case_id = root.find("case_id");
    if (case_id == nullptr || case_id->type != JsonValue::String ||
        case_id->string_value.empty()) {
        throw std::runtime_error("case_id must be a non-empty string");
    }
    item.case_id = case_id->string_value;

    const JsonValue* op = root.find("op");
    if (op == nullptr || op->type != JsonValue::String || op->string_value.empty()) {
        throw std::runtime_error("op must be a non-empty string");
    }
    item.op = op->string_value;

    const JsonValue* scope = root.find("oracle_scope");
    if (scope != nullptr) {
        if (scope->type != JsonValue::String ||
            (scope->string_value != "compare" && scope->string_value != "excluded")) {
            throw std::runtime_error("oracle_scope must be 'compare' or 'excluded'");
        }
        item.scope = scope->string_value;
    }
    const JsonValue* reason = root.find("exclusion_reason");
    if (reason != nullptr) {
        if (reason->type != JsonValue::String) {
            throw std::runtime_error("exclusion_reason must be a string");
        }
        item.exclusion_reason = reason->string_value;
    }
    if (item.scope == "excluded" && item.exclusion_reason.empty()) {
        throw std::runtime_error("excluded case requires exclusion_reason");
    }
    if (item.scope == "compare" && !item.exclusion_reason.empty()) {
        throw std::runtime_error("compare case cannot have exclusion_reason");
    }

    const JsonValue* inputs = root.find("inputs");
    if (inputs == nullptr) {
        throw std::runtime_error("missing inputs");
    }

    if (item.op != "days_from_civil" && item.op != "civil_from_days" &&
        item.op != "weekday_from_days" && item.op != "ymd_ok" &&
        item.op != "iso_weekday_from_days") {
        throw std::runtime_error("unknown operation: " + item.op);
    }

    if (item.scope == "compare") {
        if (item.op == "days_from_civil" || item.op == "ymd_ok") {
            require_exactly(*inputs, {"y", "m", "d"});
            item.y = require_int(*inputs, "y");
            item.m = require_int(*inputs, "m");
            item.d = require_int(*inputs, "d");
            if (!in_range(item.y, kYearMin, kYearMax)) {
                throw std::runtime_error("y out of i16 domain: " + std::to_string(item.y));
            }
            if (!in_range(item.m, kMonthMin, kMonthMax)) {
                throw std::runtime_error("m out of u8 domain: " + std::to_string(item.m));
            }
            if (!in_range(item.d, kDayMin, kDayMax)) {
                throw std::runtime_error("d out of u8 domain: " + std::to_string(item.d));
            }
        } else {
            require_exactly(*inputs, {"z"});
            item.z = require_int(*inputs, "z");
            if (!in_range(item.z, kI32Min, kI32Max)) {
                throw std::runtime_error("z out of i32 domain: " + std::to_string(item.z));
            }
            if (item.op == "civil_from_days" && !in_range(item.z, kZMin, kZMax)) {
                throw std::runtime_error(
                    "z outside the defined civil_from_days range [" +
                    std::to_string(kZMin) + ", " + std::to_string(kZMax) + "]: " +
                    std::to_string(item.z));
            }
        }
    }
    (void)line_number;
    return item;
}

// ---------------------------------------------------------------------------
// Operation execution against the pinned upstream checkout
// ---------------------------------------------------------------------------

std::string run_days_from_civil(long long y, long long m, long long d) {
    using namespace date;
    auto dt = year_month_day{year{static_cast<int>(y)},
                             month{static_cast<unsigned>(m)},
                             day{static_cast<unsigned>(d)}};
    auto sd = sys_days{dt};
    long long count = sd.time_since_epoch().count();
    return "\"status\":\"ok\",\"value\":" + std::to_string(count);
}

std::string run_civil_from_days(long long z) {
    using namespace date;
    auto sd = sys_days{days{static_cast<int>(z)}};
    auto dt = year_month_day{sd};
    long long y = static_cast<long long>(static_cast<int>(dt.year()));
    long long m = static_cast<long long>(static_cast<unsigned>(dt.month()));
    long long d = static_cast<long long>(static_cast<unsigned>(dt.day()));
    return "\"status\":\"ok\",\"value\":{\"y\":" + std::to_string(y) +
           ",\"m\":" + std::to_string(m) + ",\"d\":" + std::to_string(d) + "}";
}

std::string run_weekday_from_days(long long z) {
    using namespace date;
    auto sd = sys_days{days{static_cast<int>(z)}};
    auto wd = weekday{sd};
    long long enc = static_cast<long long>(wd.c_encoding());
    return "\"status\":\"ok\",\"value\":" + std::to_string(enc);
}

std::string run_ymd_ok(long long y, long long m, long long d) {
    using namespace date;
    auto dt = year_month_day{year{static_cast<int>(y)},
                             month{static_cast<unsigned>(m)},
                             day{static_cast<unsigned>(d)}};
    bool ok = dt.ok();
    return std::string("\"status\":\"ok\",\"value\":") + (ok ? "true" : "false");
}

std::string run_iso_weekday_from_days(long long z) {
    using namespace date;
    using namespace iso_week;
    auto sd = sys_days{days{static_cast<int>(z)}};
    auto wd = iso_week::weekday{sd};
    long long enc = static_cast<long long>(static_cast<unsigned>(wd));
    return "\"status\":\"ok\",\"value\":" + std::to_string(enc);
}

void write_result(std::ostream& output, const Case& item, const std::string& result) {
    output << "{\"case_id\":\"" << item.case_id << "\"," << result << "}\n";
}

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "usage: oracle_driver <cases.jsonl> <results.jsonl>\n";
        return 1;
    }
    std::ifstream input(argv[1]);
    if (!input) {
        std::cerr << "cannot open cases file: " << argv[1] << "\n";
        return 1;
    }
    std::vector<Case> cases;
    std::set<std::string> case_ids;
    std::string line;
    int line_number = 0;
    while (std::getline(input, line)) {
        ++line_number;
        if (line.empty()) {
            std::cerr << "blank line at " << argv[1] << ":" << line_number << "\n";
            return 2;
        }
        Case item;
        try {
            item = parse_case(line, line_number);
        } catch (const std::exception& error) {
            std::cerr << argv[1] << ":" << line_number << ": " << error.what() << "\n";
            return 2;
        }
        if (!case_ids.insert(item.case_id).second) {
            std::cerr << argv[1] << ":" << line_number
                      << ": duplicate case_id: " << item.case_id << "\n";
            return 2;
        }
        cases.push_back(item);
    }
    if (input.bad()) {
        std::cerr << "read error on cases file\n";
        return 1;
    }
    std::sort(cases.begin(), cases.end(), [](const Case& left, const Case& right) {
        return left.case_id < right.case_id;
    });
    std::ofstream output(argv[2]);
    if (!output) {
        std::cerr << "cannot open results file: " << argv[2] << "\n";
        return 1;
    }
    for (const Case& item : cases) {
        if (item.scope == "excluded") {
            write_result(output, item, "\"status\":\"ok\",\"value\":null");
            continue;
        }
        if (item.op == "days_from_civil") {
            write_result(output, item, run_days_from_civil(item.y, item.m, item.d));
        } else if (item.op == "civil_from_days") {
            write_result(output, item, run_civil_from_days(item.z));
        } else if (item.op == "weekday_from_days") {
            write_result(output, item, run_weekday_from_days(item.z));
        } else if (item.op == "ymd_ok") {
            write_result(output, item, run_ymd_ok(item.y, item.m, item.d));
        } else if (item.op == "iso_weekday_from_days") {
            write_result(output, item, run_iso_weekday_from_days(item.z));
        }
    }
    output.flush();
    if (!output) {
        std::cerr << "failed to flush results file\n";
        return 1;
    }
    return 0;
}
