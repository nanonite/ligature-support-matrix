#include <absl/container/flat_hash_map.h>

#include <algorithm>
#include <charconv>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <utility>
#include <variant>
#include <vector>

namespace {

struct JsonValue {
  using Object = std::map<std::string, JsonValue>;
  std::variant<std::string, Object> value;
};

class JsonParser {
 public:
  explicit JsonParser(const std::string& input) : input_(input) {}

  JsonValue parse() {
    skip_space();
    JsonValue result = parse_object();
    skip_space();
    if (position_ != input_.size()) fail("trailing JSON data");
    return result;
  }

 private:
  const std::string& input_;
  size_t position_ = 0;

  [[noreturn]] void fail(const char* message) const {
    throw std::runtime_error(std::string(message) + " at byte " +
                             std::to_string(position_));
  }

  void skip_space() {
    while (position_ < input_.size() &&
           (input_[position_] == ' ' || input_[position_] == '\t' ||
            input_[position_] == '\r' || input_[position_] == '\n')) {
      ++position_;
    }
  }

  bool consume(char expected) {
    if (position_ < input_.size() && input_[position_] == expected) {
      ++position_;
      return true;
    }
    return false;
  }

  static unsigned hex_value(char c) {
    if (c >= '0' && c <= '9') return static_cast<unsigned>(c - '0');
    if (c >= 'a' && c <= 'f') return static_cast<unsigned>(c - 'a' + 10);
    if (c >= 'A' && c <= 'F') return static_cast<unsigned>(c - 'A' + 10);
    throw std::runtime_error("invalid hexadecimal escape");
  }

  std::string parse_string() {
    if (!consume('"')) fail("expected JSON string");
    std::string result;
    while (position_ < input_.size()) {
      const unsigned char c = static_cast<unsigned char>(input_[position_++]);
      if (c == '"') return result;
      if (c < 0x20) fail("unescaped control byte in JSON string");
      if (c != '\\') {
        result.push_back(static_cast<char>(c));
        continue;
      }
      if (position_ == input_.size()) fail("truncated JSON escape");
      const char escaped = input_[position_++];
      switch (escaped) {
        case '"': result.push_back('"'); break;
        case '\\': result.push_back('\\'); break;
        case '/': result.push_back('/'); break;
        case 'b': result.push_back('\b'); break;
        case 'f': result.push_back('\f'); break;
        case 'n': result.push_back('\n'); break;
        case 'r': result.push_back('\r'); break;
        case 't': result.push_back('\t'); break;
        case 'u': {
          if (position_ + 4 > input_.size()) fail("truncated unicode escape");
          unsigned codepoint = 0;
          for (int i = 0; i < 4; ++i) {
            codepoint = codepoint * 16 + hex_value(input_[position_++]);
          }
          if (codepoint <= 0x7f) {
            result.push_back(static_cast<char>(codepoint));
          } else if (codepoint <= 0x7ff) {
            result.push_back(static_cast<char>(0xc0 | (codepoint >> 6)));
            result.push_back(static_cast<char>(0x80 | (codepoint & 0x3f)));
          } else {
            result.push_back(static_cast<char>(0xe0 | (codepoint >> 12)));
            result.push_back(static_cast<char>(0x80 | ((codepoint >> 6) & 0x3f)));
            result.push_back(static_cast<char>(0x80 | (codepoint & 0x3f)));
          }
          break;
        }
        default: fail("invalid JSON escape");
      }
    }
    fail("unterminated JSON string");
  }

  JsonValue parse_value() {
    skip_space();
    if (position_ < input_.size() && input_[position_] == '"') {
      return JsonValue{parse_string()};
    }
    if (position_ < input_.size() && input_[position_] == '{') {
      return parse_object();
    }
    fail("case schema permits only strings and objects");
  }

  JsonValue parse_object() {
    if (!consume('{')) fail("expected JSON object");
    JsonValue::Object object;
    skip_space();
    if (consume('}')) return JsonValue{std::move(object)};
    while (true) {
      skip_space();
      std::string key = parse_string();
      skip_space();
      if (!consume(':')) fail("expected colon");
      JsonValue item = parse_value();
      if (!object.emplace(std::move(key), std::move(item)).second) {
        fail("duplicate object field");
      }
      skip_space();
      if (consume('}')) return JsonValue{std::move(object)};
      if (!consume(',')) fail("expected comma or object end");
    }
  }
};

const JsonValue::Object& as_object(const JsonValue& value,
                                  const std::string& where) {
  const auto* object = std::get_if<JsonValue::Object>(&value.value);
  if (object == nullptr) throw std::runtime_error(where + " must be an object");
  return *object;
}

const std::string& as_string(const JsonValue& value,
                             const std::string& where) {
  const auto* string = std::get_if<std::string>(&value.value);
  if (string == nullptr) throw std::runtime_error(where + " must be a string");
  return *string;
}

const JsonValue& require_field(const JsonValue::Object& object,
                               const std::string& name,
                               const std::string& where) {
  const auto found = object.find(name);
  if (found == object.end()) {
    throw std::runtime_error(where + " is missing required field " + name);
  }
  return found->second;
}

void reject_unknown_fields(const JsonValue::Object& object,
                           const std::set<std::string>& allowed,
                           const std::string& where) {
  for (const auto& [key, unused] : object) {
    (void)unused;
    if (allowed.find(key) == allowed.end()) {
      throw std::runtime_error(where + " has unknown field " + key);
    }
  }
}

struct Action {
  std::string kind;
  uint64_t first = 0;
  uint64_t second = 0;
  std::string source;
};

uint64_t parse_u64(const std::string& text, const std::string& where) {
  if (text.empty() || (text.size() > 1 && text.front() == '0')) {
    throw std::runtime_error(where + " is not a canonical unsigned integer");
  }
  uint64_t value = 0;
  const auto result =
      std::from_chars(text.data(), text.data() + text.size(), value);
  if (result.ec != std::errc{} || result.ptr != text.data() + text.size()) {
    throw std::runtime_error(where + " is not a uint64");
  }
  return value;
}

Action parse_action(const std::string& text) {
  const size_t open = text.find('(');
  if (open == std::string::npos || text.back() != ')') {
    throw std::runtime_error("malformed action: " + text);
  }
  const std::string kind = text.substr(0, open);
  const std::string args = text.substr(open + 1, text.size() - open - 2);
  Action action{kind, 0, 0, text};
  if (kind == "clear" || kind == "erase_if_all" ||
      kind == "erase_if_none" || kind == "erase_if_odd") {
    if (!args.empty()) throw std::runtime_error(kind + " takes no arguments");
    return action;
  }
  const size_t comma = args.find(',');
  if (kind == "insert") {
    if (comma == std::string::npos || args.find(',', comma + 1) != std::string::npos) {
      throw std::runtime_error("insert requires exactly two arguments");
    }
    action.first = parse_u64(args.substr(0, comma), "insert key");
    action.second = parse_u64(args.substr(comma + 1), "insert value");
    return action;
  }
  if (kind == "erase" || kind == "contains" || kind == "reserve") {
    if (comma != std::string::npos) {
      throw std::runtime_error(kind + " requires exactly one argument");
    }
    action.first = parse_u64(args, kind + " argument");
    return action;
  }
  throw std::runtime_error("unknown action: " + kind);
}

std::vector<Action> parse_actions(const std::string& text) {
  if (text.empty()) throw std::runtime_error("actions must not be empty");
  std::vector<Action> actions;
  size_t start = 0;
  while (start < text.size()) {
    const size_t end = text.find(';', start);
    const std::string part = text.substr(
        start, end == std::string::npos ? std::string::npos : end - start);
    if (part.empty()) throw std::runtime_error("empty action in sequence");
    actions.push_back(parse_action(part));
    if (end == std::string::npos) break;
    start = end + 1;
    if (start == text.size()) throw std::runtime_error("trailing action separator");
  }
  return actions;
}

struct Case {
  std::string id;
  std::string op;
  std::string actions_text;
  std::vector<Action> actions;
  std::string scope = "compare";
  std::optional<std::string> exclusion_reason;
};

Case parse_case(const std::string& line) {
  const JsonValue parsed = JsonParser(line).parse();
  const auto& object = as_object(parsed, "case");
  reject_unknown_fields(
      object, {"case_id", "op", "inputs", "oracle_scope", "exclusion_reason"},
      "case");

  Case item;
  item.id = as_string(require_field(object, "case_id", "case"), "case_id");
  static const std::regex id_pattern("^[a-z0-9]+(-[a-z0-9]+)*$");
  if (!std::regex_match(item.id, id_pattern)) {
    throw std::runtime_error("case_id is not stable lower-case ASCII: " + item.id);
  }
  item.op = as_string(require_field(object, "op", "case"), "op");
  if (item.op != "map_sequence") {
    throw std::runtime_error("unknown operation: " + item.op);
  }
  const auto& inputs = as_object(require_field(object, "inputs", "case"), "inputs");
  reject_unknown_fields(inputs, {"actions"}, "inputs");
  item.actions_text =
      as_string(require_field(inputs, "actions", "inputs"), "inputs.actions");
  item.actions = parse_actions(item.actions_text);

  const auto scope = object.find("oracle_scope");
  if (scope != object.end()) item.scope = as_string(scope->second, "oracle_scope");
  const auto reason = object.find("exclusion_reason");
  if (reason != object.end()) {
    item.exclusion_reason = as_string(reason->second, "exclusion_reason");
  }
  if (item.scope == "compare") {
    if (item.exclusion_reason.has_value()) {
      throw std::runtime_error("compare case must not have exclusion_reason");
    }
    for (const Action& action : item.actions) {
      if ((action.kind == "insert" || action.kind == "erase" ||
           action.kind == "contains") &&
          action.first == 0) {
        throw std::runtime_error("key zero is outside the Rust comparison domain");
      }
    }
  } else if (item.scope == "excluded") {
    if (!item.exclusion_reason.has_value() ||
        item.exclusion_reason->find_first_not_of(" \t\r\n") == std::string::npos) {
      throw std::runtime_error("excluded case requires a non-empty reason");
    }
  } else {
    throw std::runtime_error("oracle_scope must be compare or excluded");
  }
  return item;
}

struct IdentityHash {
  size_t operator()(uint64_t key) const noexcept { return static_cast<size_t>(key); }
};
static_assert(sizeof(size_t) == sizeof(uint64_t),
              "the shared IdentityHash-v1 requires a 64-bit size_t");

using Map = absl::flat_hash_map<uint64_t, uint64_t, IdentityHash>;
using Entry = std::pair<uint64_t, uint64_t>;

std::vector<Entry> sorted_entries(const Map& map) {
  std::vector<Entry> entries;
  entries.reserve(map.size());
  for (const auto& [key, value] : map) entries.emplace_back(key, value);
  std::sort(entries.begin(), entries.end());
  return entries;
}

std::string entries_json(const std::vector<Entry>& entries) {
  std::ostringstream out;
  out << '[';
  for (size_t i = 0; i < entries.size(); ++i) {
    if (i != 0) out << ',';
    out << '[' << entries[i].first << ',' << entries[i].second << ']';
  }
  out << ']';
  return out.str();
}

std::string json_string(const std::string& value) {
  std::ostringstream out;
  out << '"';
  for (unsigned char c : value) {
    switch (c) {
      case '"': out << "\\\""; break;
      case '\\': out << "\\\\"; break;
      case '\b': out << "\\b"; break;
      case '\f': out << "\\f"; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 0x20) {
          const char* digits = "0123456789abcdef";
          out << "\\u00" << digits[c >> 4] << digits[c & 0xf];
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  out << '"';
  return out.str();
}

std::string run_case(const Case& item) {
  if (item.scope == "excluded") {
    return "{\"case_id\":" + json_string(item.id) +
           ",\"status\":\"ok\",\"value\":null}";
  }

  Map map;
  std::ostringstream observations;
  observations << '[';
  for (size_t index = 0; index < item.actions.size(); ++index) {
    const Action& action = item.actions[index];
    if (index != 0) observations << ',';

    std::string result = "null";
    if (action.kind == "insert") {
      const auto [unused, inserted] = map.insert_or_assign(action.first, action.second);
      (void)unused;
      result = inserted ? "true" : "false";
    } else if (action.kind == "erase") {
      result = map.erase(action.first) == 1 ? "true" : "false";
    } else if (action.kind == "contains") {
      result = map.contains(action.first) ? "true" : "false";
    } else if (action.kind == "reserve") {
      if (action.first > std::numeric_limits<size_t>::max() - map.size()) {
        throw std::runtime_error("reserve target exceeds size_t");
      }
      map.reserve(map.size() + static_cast<size_t>(action.first));
    } else if (action.kind == "clear") {
      map.clear();
    } else if (action.kind == "erase_if_all") {
      result = std::to_string(absl::erase_if(map, [](const auto&) { return true; }));
    } else if (action.kind == "erase_if_none") {
      result = std::to_string(absl::erase_if(map, [](const auto&) { return false; }));
    } else if (action.kind == "erase_if_odd") {
      result = std::to_string(absl::erase_if(
          map, [](const auto& entry) { return (entry.first & 1u) != 0; }));
    } else {
      throw std::runtime_error("internal unknown action: " + action.kind);
    }
    observations << "{\"action\":" << json_string(action.source)
                 << ",\"result\":" << result << ",\"size\":" << map.size()
                 << ",\"entries\":" << entries_json(sorted_entries(map)) << '}';
  }
  observations << ']';

  const std::string value =
      "{\"observations\":" + observations.str() +
      ",\"final_entries\":" + entries_json(sorted_entries(map)) + '}';
  return "{\"case_id\":" + json_string(item.id) +
         ",\"status\":\"ok\",\"value\":" + value + '}';
}

std::vector<Case> read_cases(const std::string& path) {
  std::ifstream input(path, std::ios::binary);
  if (!input) throw std::runtime_error("cannot open case file: " + path);
  std::vector<Case> cases;
  std::set<std::string> ids;
  std::string line;
  size_t line_number = 0;
  while (std::getline(input, line)) {
    ++line_number;
    if (line.empty()) {
      throw std::runtime_error("blank line in case file at line " +
                               std::to_string(line_number));
    }
    Case item;
    try {
      item = parse_case(line);
    } catch (const std::exception& error) {
      throw std::runtime_error("invalid case line " + std::to_string(line_number) +
                               ": " + error.what());
    }
    if (!ids.insert(item.id).second) {
      throw std::runtime_error("duplicate case_id: " + item.id);
    }
    cases.push_back(std::move(item));
  }
  if (input.bad()) throw std::runtime_error("error reading case file: " + path);
  if (cases.empty()) throw std::runtime_error("case file must contain at least one case");
  std::sort(cases.begin(), cases.end(),
            [](const Case& a, const Case& b) { return a.id < b.id; });
  return cases;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: oracle_driver <cases.jsonl> <results.jsonl>\n";
    return 2;
  }
  try {
    const std::vector<Case> cases = read_cases(argv[1]);
    std::ofstream output(argv[2], std::ios::binary | std::ios::trunc);
    if (!output) throw std::runtime_error("cannot open result file: " + std::string(argv[2]));
    for (const Case& item : cases) output << run_case(item) << '\n';
    output.flush();
    if (!output) throw std::runtime_error("failed to flush result file");
    return 0;
  } catch (const std::exception& error) {
    std::cerr << "oracle_driver: " << error.what() << '\n';
    return 1;
  }
}
