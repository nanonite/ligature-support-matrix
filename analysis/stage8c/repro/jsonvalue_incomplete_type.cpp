#include <string>
#include <utility>
#include <vector>
struct JsonValue {
  std::vector<std::pair<std::string, JsonValue>> object_value;
  const JsonValue* find(const std::string& k) const { for (const auto& m : object_value) if (m.first == k) return &m.second; return nullptr; }
};
int main() { JsonValue v; return v.find("a") != nullptr; }
