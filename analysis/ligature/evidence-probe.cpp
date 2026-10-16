// Evidence probe for chainlink #13 (Stage 0 evidence intake).
//
// Purpose: produce the `observed-behavior` source material that evidence
// records E-13 (weekday encodings) and E-14 (era round-trip + validity) are
// drawn from. It is a read-only observer of the pinned HowardHinnant/date
// v3.0.5 header at 179a6b921ccd6179b5b04dce812a89f71a51b4df -- it writes
// nothing and touches no file under upstream/.
//
// It is NOT the differential oracle. `oracle/` belongs to chainlink #17; this
// probe exists only so that `observed-behavior` evidence is an observation and
// not a paraphrase of the source.
//
// Only the PUBLIC surface is used. `year_month_day::to_days()` and
// `year_month_day::from_days()` are private members (include/date/date.h
// lines 726-728), so the era arithmetic is only reachable through
// `operator sys_days()`, `operator local_days()` and the
// `year_month_day(sys_days)` constructor. That is itself part of what the
// evidence records state.
//
// Build (from the pilot root):
//   g++ -std=c++20 -I upstream/date/include analysis/ligature/evidence-probe.cpp

#include "date/date.h"
#include "date/iso_week.h"

#include <cstdio>
#include <limits>

namespace
{

// Deterministic sample: the epoch, the z >= -4 branch boundary in
// weekday_from_days, the 400-year era boundaries, the Gregorian leap
// century cases, and both ends of the representable year domain.
struct Sample { int y; unsigned m; unsigned d; };

const Sample kSamples[] = {
    {1970, 1, 1},                  // epoch
    {1969, 12, 31},                // one day before the epoch
    {1970, 1, 2},                  // 1970-01-01 + 1
    {1970, 1, 4},                  // 1970-01-04 is the first date::weekday 0 (Sunday)
    {1969, 12, 27},                // epoch - 5  (one before the z >= -4 branch)
    {1969, 12, 28},                // epoch - 4  (the z >= -4 branch itself)
    {2000, 2, 29},                 // leap century (divisible by 400)
    {1900, 2, 29},                 // NOT a leap year -> ok() must be false
    {1900, 3, 1},
    {2024, 2, 29},                 // leap year
    {2023, 2, 29},                 // NOT a leap year -> ok() must be false
    {1600, 1, 1},                  // era 4 boundary
    {1599, 12, 31},                // era 3 / 4 boundary
    {1, 1, 1},                     // positive low
    {0, 1, 1},                     // astronomical year 0
    {-1, 12, 31},                  // first negative year
    {date::year::min().operator int(), 1, 1},     // most negative representable year
    {date::year::max().operator int(), 12, 31}    // most positive representable year
};

const int kDays[] = {0, -1, -4, -5, 3, 4};

}  // namespace

int
main()
{
    // E-13: the date::weekday encoding and its ISO re-encoding.
    for (int z : kDays)
    {
        date::sys_days sd{date::days{z}};
        date::weekday wd{sd};
        iso_week::weekday iwd{sd};
        std::printf("z=%-8d date::weekday.c_encoding()=%u iso_week::weekday=%u\n", z,
                    wd.c_encoding(), static_cast<unsigned>(iwd));
    }

    // E-14: validity and the sys_days round trip over the deterministic sample.
    // `operator sys_days()` is total -- it is NOT guarded by ok() -- so the
    // round trip is reported for every sample, and separately counted only
    // over the ok() ones, because an out-of-range day is silently normalized
    // by the era arithmetic rather than rejected.
    int checked = 0, ok_true = 0, ok_false = 0, roundtrip_ok = 0, roundtrip_bad = 0;
    for (auto const& s : kSamples)
    {
        date::year_month_day const ymd{date::year{s.y}, date::month(s.m), date::day(s.d)};
        bool const ok = ymd.ok();
        ok_true += ok ? 1 : 0;
        ok_false += ok ? 0 : 1;

        date::sys_days const sd{ymd};
        date::year_month_day const back{sd};
        bool const same = (back == ymd);
        if (ok)
        {
            roundtrip_ok += same ? 1 : 0;
            roundtrip_bad += same ? 0 : 1;
        }
        std::printf("ymd(%d,%u,%u).ok()=%d sys_days=%lld weekday=%u "
                    "from_days(sys_days)=(%d,%u,%u) identical=%d\n",
                    s.y, s.m, s.d, ok ? 1 : 0,
                    static_cast<long long>(sd.time_since_epoch().count()),
                    date::weekday(sd).c_encoding(), back.year().operator int(),
                    static_cast<unsigned>(back.month()), static_cast<unsigned>(back.day()),
                    same ? 1 : 0);
        ++checked;
    }
    std::printf(
        "E-14 totals checked=%d ok_true=%d ok_false=%d roundtrip_ok=%d roundtrip_bad=%d\n",
        checked, ok_true, ok_false, roundtrip_ok, roundtrip_bad);

    // E-12: the representable year domain and the single value ok() excludes.
    std::printf(
        "year::min()=%d year::max()=%d year(-32768).ok()=%d year(-32767).ok()=%d "
        "year(32767).ok()=%d sizeof(short)=%zu numeric_limits<short>::min=%d "
        "numeric_limits<int>::digits=%d numeric_limits<unsigned>::digits=%d\n",
        date::year::min().operator int(), date::year::max().operator int(),
        date::year{-32768}.ok() ? 1 : 0, date::year{-32767}.ok() ? 1 : 0,
        date::year{32767}.ok() ? 1 : 0, sizeof(short),
        std::numeric_limits<short>::min(), std::numeric_limits<int>::digits,
        std::numeric_limits<unsigned>::digits);
    return 0;
}
