#include <algorithm>
#include <cctype>
#include <fstream>
#include <iostream>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

struct Case {
    std::string case_id;
    std::string op;
    std::string scope = "compare";
    std::string exclusion_reason;
    long long a = 0;
    long long b = 0;
};

std::string field(const std::string& line, const std::string& key) {
    const std::string marker = "\"" + key + "\":";
    const std::size_t position = line.find(marker);
    if (position == std::string::npos) {
        return "";
    }
    std::size_t start = position + marker.size();
    while (start < line.size() && std::isspace(static_cast<unsigned char>(line[start]))) {
        ++start;
    }
    if (start >= line.size() || line[start] != '"') {
        return "";
    }
    ++start;
    const std::size_t end = line.find('"', start);
    if (end == std::string::npos) {
        throw std::runtime_error("unterminated string field: " + key);
    }
    return line.substr(start, end - start);
}

long long number_field(const std::string& line, const std::string& key) {
    const std::string marker = "\"" + key + "\":";
    const std::size_t position = line.find(marker);
    if (position == std::string::npos) {
        throw std::runtime_error("missing numeric field: " + key);
    }
    std::size_t start = position + marker.size();
    while (start < line.size() && std::isspace(static_cast<unsigned char>(line[start]))) {
        ++start;
    }
    std::size_t end = start;
    if (end < line.size() && (line[end] == '-' || line[end] == '+')) {
        ++end;
    }
    while (end < line.size() && std::isdigit(static_cast<unsigned char>(line[end]))) {
        ++end;
    }
    if (end == start) {
        throw std::runtime_error("invalid numeric field: " + key);
    }
    return std::stoll(line.substr(start, end - start));
}

Case parse_case(const std::string& line) {
    Case item;
    item.case_id = field(line, "case_id");
    item.op = field(line, "op");
    item.scope = field(line, "oracle_scope");
    if (item.scope.empty()) {
        item.scope = "compare";
    }
    item.exclusion_reason = field(line, "exclusion_reason");
    if (item.case_id.empty() || item.op.empty()) {
        throw std::runtime_error("case_id and op are required");
    }
    if (item.scope != "compare" && item.scope != "excluded") {
        throw std::runtime_error("invalid oracle_scope");
    }
    if (item.scope == "excluded" && item.exclusion_reason.empty()) {
        throw std::runtime_error("excluded cases require exclusion_reason");
    }
    if (item.scope == "compare" && !item.exclusion_reason.empty()) {
        throw std::runtime_error("compare cases cannot have exclusion_reason");
    }
    if (item.scope == "compare" && item.op == "add") {
        item.a = number_field(line, "a");
        item.b = number_field(line, "b");
    }
    return item;
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
        std::cerr << "cannot open cases file\n";
        return 1;
    }
    std::vector<Case> cases;
    std::set<std::string> case_ids;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) {
            continue;
        }
        Case item = parse_case(line);
        if (!case_ids.insert(item.case_id).second) {
            throw std::runtime_error("duplicate case_id: " + item.case_id);
        }
        cases.push_back(item);
    }
    std::sort(cases.begin(), cases.end(), [](const Case& left, const Case& right) {
        return left.case_id < right.case_id;
    });
    std::ofstream output(argv[2]);
    if (!output) {
        std::cerr << "cannot open results file\n";
        return 1;
    }
    for (const Case& item : cases) {
        if (item.scope == "excluded") {
            write_result(output, item, "\"status\":\"ok\",\"value\":null");
            continue;
        }
        if (item.op != "add") {
            throw std::runtime_error("unknown operation: " + item.op);
        }
        const long long maximum = std::numeric_limits<long long>::max();
        const long long minimum = std::numeric_limits<long long>::min();
        if ((item.b > 0 && item.a > maximum - item.b) ||
            (item.b < 0 && item.a < minimum - item.b)) {
            write_result(output, item, "\"status\":\"err\",\"err_kind\":\"integer_overflow\"");
        } else {
            write_result(output, item, "\"status\":\"ok\",\"value\":" + std::to_string(item.a + item.b));
        }
    }
    return 0;
}
