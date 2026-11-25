import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import {
  addBusinessDays,
  Calendar,
  type CalendarOptions,
  CONFIRMED_UNTIL,
  FIRST_YEAR,
  holiday,
  holidays,
  isBusinessDay,
  isHoliday,
  nextBusinessDay,
  previousBusinessDay,
  toISODate,
} from "../src/index.js";

const root = new URL("../../", import.meta.url);
interface RawOptions {
  saturday_is_workday?: boolean;
  half_days?: CalendarOptions["halfDays"];
  extra_holidays?: string[];
  extra_workdays?: string[];
  allow_estimated?: boolean;
}

type Case = { options?: RawOptions } & Record<string, any>;

type Section =
  | "is_business_day"
  | "holiday_key"
  | "add_business_days"
  | "business_days_between"
  | "deadline"
  | "bridge_days"
  | "holiday_count"
  | "out_of_range";

const cases: Record<Section, Case[]> = JSON.parse(
  readFileSync(new URL("fixtures/cases.json", root), "utf8"),
);

function cal(c: Case): Calendar {
  const o = c.options ?? {};
  return new Calendar({
    saturdayIsWorkday: o.saturday_is_workday,
    halfDays: o.half_days,
    extraHolidays: o.extra_holidays,
    extraWorkdays: o.extra_workdays,
    allowEstimated: o.allow_estimated,
  });
}

function addDays(iso: string, n: number): string {
  return new Date(Date.parse(iso) + n * 86_400_000).toISOString().slice(0, 10);
}

// Written out by hand from the Diyanet calendar.
const BAYRAMS: Record<number, [string, string]> = {
  2023: ["2023-04-21", "2023-06-28"],
  2024: ["2024-04-10", "2024-06-16"],
  2025: ["2025-03-30", "2025-06-06"],
  2026: ["2026-03-20", "2026-05-27"],
  2027: ["2027-03-09", "2027-05-16"],
};

describe("official dates", () => {
  for (const [year, [ramazan, kurban]] of Object.entries(BAYRAMS)) {
    it(`bayrams of ${year}`, () => {
      for (const [start, key, days] of [
        [ramazan, "ramazan", 3],
        [kurban, "kurban", 4],
      ] as const) {
        const eve = holiday(addDays(start, -1));
        expect(eve?.key).toBe(`${key}_arifesi`);
        expect(eve?.half).toBe(true);
        for (let i = 0; i < days; i++) {
          expect(holiday(addDays(start, i))?.key).toBe(`${key}_${i + 1}`);
        }
        expect(holiday(addDays(start, days))?.key.startsWith(key) ?? false).toBe(false);
      }
    });
  }

  it("15 July starts in 2017", () => {
    expect(holiday("2016-07-15")).toBeNull();
    expect(holiday("2017-07-15")?.key).toBe("demokrasi");
  });

  it("half days are the three eves", () => {
    expect(holidays(2026).filter((h) => h.half).map((h) => [h.date, h.key])).toEqual([
      ["2026-03-19", "ramazan_arifesi"],
      ["2026-05-26", "kurban_arifesi"],
      ["2026-10-28", "cumhuriyet_arifesi"],
    ]);
  });

  it("confirmed years are not estimated", () => {
    for (let y = FIRST_YEAR; y <= CONFIRMED_UNTIL; y++) {
      expect(holidays(y).some((h) => h.estimated)).toBe(false);
    }
  });

  it("Turkish names", () => {
    expect(holiday("2026-05-19")?.name).toBe("Atatürk'ü Anma, Gençlik ve Spor Bayramı");
    expect(holiday("2026-07-15")?.nameEn).toBe("Democracy and National Unity Day");
  });
});

describe("shared fixtures", () => {
  it.each<Case>(cases.is_business_day)("isBusinessDay $date $options", (c) => {
    expect(cal(c).isBusinessDay(c.date)).toBe(c.expect);
  });
  it.each<Case>(cases.holiday_key)("holiday $date", (c) => {
    expect(cal(c).holiday(c.date)?.key ?? null).toBe(c.expect);
  });
  it.each<Case>(cases.add_business_days)("addBusinessDays $date $n $options", (c) => {
    expect(cal(c).addBusinessDays(c.date, c.n)).toBe(c.expect);
  });
  it.each<Case>(cases.business_days_between)("businessDaysBetween $start $end $options", (c) => {
    expect(cal(c).businessDaysBetween(c.start, c.end)).toBe(c.expect);
  });
  it.each<Case>(cases.deadline)("deadline $date +$days", (c) => {
    expect(cal(c).deadline(c.date, c.days)).toBe(c.expect);
  });
  it.each<Case>(cases.bridge_days)("bridgeDays $year $options", (c) => {
    expect(cal(c).bridgeDays(c.year)).toEqual(c.expect);
  });
  it.each<Case>(cases.holiday_count)("holidays($year).length", (c) => {
    expect(cal(c).holidays(c.year)).toHaveLength(c.expect);
  });
  it.each<Case>(cases.out_of_range)("out of range $date", (c) => {
    expect(() => cal(c).isBusinessDay(c.date)).toThrow(RangeError);
  });
});

describe("inputs", () => {
  it("strings: a time part is ignored", () => {
    expect(isBusinessDay("2026-03-20T09:30:00+03:00")).toBe(false);
    expect(toISODate(" 2026-03-20 ")).toBe("2026-03-20");
  });

  it("Date objects are read as the day in Türkiye", () => {
    // 21:30 UTC on 19 March is already 20 March (bayram) in Istanbul.
    expect(toISODate(new Date("2026-03-19T21:30:00Z"))).toBe("2026-03-20");
    expect(isHoliday(new Date("2026-03-19T21:30:00Z"))).toBe(true);
    expect(toISODate(new Date("2026-03-20T00:00:00Z"))).toBe("2026-03-20");
  });

  it("rejects bad input", () => {
    expect(() => isBusinessDay("20.03.2026")).toThrow(TypeError);
    expect(() => isBusinessDay("2026-02-30")).toThrow(RangeError);
    expect(() => isBusinessDay(new Date("nope"))).toThrow(TypeError);
    expect(() => addBusinessDays("2026-03-18", 1.5)).toThrow(TypeError);
    expect(() => new Calendar({ halfDays: "sometimes" as never })).toThrow(RangeError);
  });

  it("estimated years need the option", () => {
    expect(() => holidays(2040)).toThrow(/allowEstimated/);
    expect(new Calendar({ allowEstimated: true }).holidays(2040).length).toBeGreaterThan(0);
  });

  it("next / previous", () => {
    expect(nextBusinessDay("2026-03-19")).toBe("2026-03-23");
    expect(previousBusinessDay("2026-03-23")).toBe("2026-03-19");
  });

  it("returned holidays cannot be changed", () => {
    const h = holiday("2026-03-20");
    expect(Object.isFrozen(h)).toBe(true);
  });
});

it("version matches the Python package", () => {
  const pkg = JSON.parse(readFileSync(fileURLToPath(new URL("js/package.json", root)), "utf8"));
  const init = readFileSync(new URL("python/src/isgunu/__init__.py", root), "utf8");
  expect(init).toContain(`__version__ = "${pkg.version}"`);
});
