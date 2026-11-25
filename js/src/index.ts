import { CONFIRMED_UNTIL, FIRST_YEAR, HOLIDAYS, LAST_YEAR } from "./data.js";

export { CONFIRMED_UNTIL, FIRST_YEAR, LAST_YEAR };

/** A `Date`, or an ISO date string such as `"2026-03-20"` (a time part is ignored). */
export type DateLike = Date | string;

/** How arife and 28 October afternoons count. */
export type HalfDays = "workday" | "holiday" | "half";

/** One holiday day. `half` days (arife, 28 October) start at 13:00. */
export interface Holiday {
  /** `YYYY-MM-DD` */
  date: string;
  key: string;
  name: string;
  nameEn: string;
  half: boolean;
  estimated: boolean;
}

export interface CalendarOptions {
  /** Count Saturdays as working days (six-day week). Default `false`. */
  saturdayIsWorkday?: boolean;
  /**
   * `"workday"` (default) treats arife afternoons as working days, `"holiday"`
   * as days off, `"half"` as working days that count 0.5 in `businessDaysBetween`.
   */
  halfDays?: HalfDays;
  /** More days off, such as the yearly administrative leave (idari izin). */
  extraHolidays?: Iterable<DateLike>;
  /** Days worked although they would be off, such as a make-up Saturday. */
  extraWorkdays?: Iterable<DateLike>;
  /**
   * Allow years after the last one confirmed against the Diyanet calendar.
   * Bayram dates there may be off by a day.
   */
  allowEstimated?: boolean;
}

const DAY_MS = 86_400_000;
const ISO = /^(\d{4})-(\d{2})-(\d{2})/;

// Date objects are read as the calendar day in Türkiye, whatever the time zone
// of the machine: `new Date()` on a UTC server still answers "is it a working
// day in Türkiye today".
const istanbul = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Europe/Istanbul",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Days since 1970-01-01. */
function toDayNumber(value: DateLike): number {
  let iso: string;
  if (value instanceof Date) {
    if (Number.isNaN(value.getTime())) throw new TypeError("invalid Date");
    iso = istanbul.format(value);
  } else if (typeof value === "string") {
    iso = value.trim();
  } else {
    throw new TypeError(`expected a Date or 'YYYY-MM-DD' string, got ${typeof value}`);
  }
  const m = ISO.exec(iso);
  if (!m) throw new TypeError(`expected 'YYYY-MM-DD', got '${iso}'`);
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const n = Date.UTC(y, mo - 1, d) / DAY_MS;
  if (fromDayNumber(n) !== `${m[1]}-${m[2]}-${m[3]}`) throw new RangeError(`no such date '${iso}'`);
  return n;
}

function fromDayNumber(n: number): string {
  return new Date(n * DAY_MS).toISOString().slice(0, 10);
}

function yearOf(n: number): number {
  return new Date(n * DAY_MS).getUTCFullYear();
}

/** 0 = Monday ... 6 = Sunday (1970-01-01 was a Thursday). */
function weekday(n: number): number {
  return (((n + 3) % 7) + 7) % 7;
}

/** Normalise a `Date` or string to `YYYY-MM-DD`. */
export function toISODate(value: DateLike): string {
  return fromDayNumber(toDayNumber(value));
}

const BY_DAY = new Map<number, Holiday[]>();
for (const [date, key, name, nameEn, half, estimated] of HOLIDAYS) {
  const n = toDayNumber(date);
  const list = BY_DAY.get(n) ?? [];
  // The table is ordered: full days first, then the bayram, then fixed holidays.
  list.push(Object.freeze({ date, key, name, nameEn, half, estimated }));
  BY_DAY.set(n, list);
}

/** A working calendar: Turkish public holidays plus your own rules. */
export class Calendar {
  readonly saturdayIsWorkday: boolean;
  readonly halfDays: HalfDays;
  readonly allowEstimated: boolean;
  private readonly extraHolidays: Set<number>;
  private readonly extraWorkdays: Set<number>;
  private readonly lastYear: number;

  constructor(options: CalendarOptions = {}) {
    const halfDays = options.halfDays ?? "workday";
    if (!["workday", "holiday", "half"].includes(halfDays)) {
      throw new RangeError("halfDays must be 'workday', 'holiday' or 'half'");
    }
    this.saturdayIsWorkday = options.saturdayIsWorkday ?? false;
    this.halfDays = halfDays;
    this.allowEstimated = options.allowEstimated ?? false;
    this.extraHolidays = new Set([...(options.extraHolidays ?? [])].map(toDayNumber));
    this.extraWorkdays = new Set([...(options.extraWorkdays ?? [])].map(toDayNumber));
    this.lastYear = this.allowEstimated ? LAST_YEAR : CONFIRMED_UNTIL;
  }

  private check(n: number): number {
    const year = yearOf(n);
    if (year < FIRST_YEAR || year > this.lastYear) {
      const hint =
        !this.allowEstimated && year > CONFIRMED_UNTIL && year <= LAST_YEAR
          ? `; years ${CONFIRMED_UNTIL + 1}-${LAST_YEAR} need allowEstimated: true`
          : "";
      throw new RangeError(
        `${year} is outside the supported years ${FIRST_YEAR}-${this.lastYear}${hint}`,
      );
    }
    return n;
  }

  /** Every holiday day of `year` in date order, half days included. */
  holidays(year: number): Holiday[] {
    this.check(Date.UTC(year, 0, 1) / DAY_MS);
    const start = Date.UTC(year, 0, 1) / DAY_MS;
    const end = Date.UTC(year + 1, 0, 1) / DAY_MS;
    const out: Holiday[] = [];
    for (let n = start; n < end; n++) out.push(...(BY_DAY.get(n) ?? []));
    return out;
  }

  /**
   * The holiday on `day`, or `null`. When two fall on the same date, a full day
   * wins over a half day and a bayram over a fixed holiday.
   */
  holiday(day: DateLike): Holiday | null {
    return BY_DAY.get(this.check(toDayNumber(day)))?.[0] ?? null;
  }

  /** True for a full-day public holiday (not arife afternoons). */
  isHoliday(day: DateLike): boolean {
    const h = this.holiday(day);
    return h !== null && !h.half;
  }

  /** 1 for a working day, 0 for a day off, 0.5 for a half day in "half" mode. */
  private weight(n: number): number {
    this.check(n);
    if (this.extraWorkdays.has(n)) return 1;
    if (this.extraHolidays.has(n)) return 0;
    const wd = weekday(n);
    if (wd === 6 || (wd === 5 && !this.saturdayIsWorkday)) return 0;
    const first = BY_DAY.get(n)?.[0];
    if (!first) return 1;
    if (!first.half) return 0;
    return this.halfDays === "workday" ? 1 : this.halfDays === "half" ? 0.5 : 0;
  }

  private isWorking(n: number): boolean {
    return this.weight(n) > 0;
  }

  /** True when `day` is a working day. */
  isBusinessDay(day: DateLike): boolean {
    return this.isWorking(toDayNumber(day));
  }

  private step(n: number, dir: 1 | -1): number {
    let d = n + dir;
    while (!this.isWorking(d)) d += dir;
    return d;
  }

  /** The first working day strictly after `day`. */
  nextBusinessDay(day: DateLike): string {
    return fromDayNumber(this.step(toDayNumber(day), 1));
  }

  /** The last working day strictly before `day`. */
  previousBusinessDay(day: DateLike): string {
    return fromDayNumber(this.step(toDayNumber(day), -1));
  }

  /**
   * Move `n` working days from `day`; negative `n` goes back. `day` itself is
   * not counted. With `n === 0` the day is returned if it is a working day,
   * otherwise the next working day.
   */
  addBusinessDays(day: DateLike, n: number): string {
    if (!Number.isInteger(n)) throw new TypeError("n must be an integer");
    let d = toDayNumber(day);
    if (n === 0) return fromDayNumber(this.isWorking(d) ? d : this.step(d, 1));
    const dir = n > 0 ? 1 : -1;
    for (let i = 0; i < Math.abs(n); i++) d = this.step(d, dir);
    return fromDayNumber(d);
  }

  /**
   * Working days in `[start, end)`: start counted, end not. Negative when `end`
   * is before `start`. A whole number unless `halfDays: "half"`.
   */
  businessDaysBetween(start: DateLike, end: DateLike): number {
    let a = toDayNumber(start);
    let b = toDayNumber(end);
    let sign = 1;
    if (b < a) {
      [a, b] = [b, a];
      sign = -1;
    }
    let total = 0;
    for (let d = a; d < b; d++) total += this.weight(d);
    return sign * total || 0;
  }

  /**
   * `start` plus `days` calendar days, moved to the next working day when it
   * falls on a weekend or holiday - how most Turkish legal and contractual
   * periods expressed in days end. Check the rule that applies to your case.
   */
  deadline(start: DateLike, days: number): string {
    if (!Number.isInteger(days)) throw new TypeError("days must be an integer");
    const d = toDayNumber(start) + days;
    return fromDayNumber(this.isWorking(d) ? d : this.step(d, 1));
  }

  /**
   * Single working days stuck between a holiday and a weekend (köprü). Taking
   * them off joins the holiday to the weekend.
   */
  bridgeDays(year: number): string[] {
    this.check(Date.UTC(year, 0, 1) / DAY_MS);
    const start = Date.UTC(year, 0, 1) / DAY_MS;
    const end = Date.UTC(year + 1, 0, 1) / DAY_MS;
    const out: string[] = [];
    for (let d = start; d < end; d++) {
      const prev = d - 1;
      const next = d + 1;
      if (
        this.isWorking(d) &&
        yearOf(prev) >= FIRST_YEAR &&
        yearOf(next) <= this.lastYear &&
        !this.isWorking(prev) &&
        !this.isWorking(next) &&
        (this.isOffHoliday(prev) || this.isOffHoliday(next))
      ) {
        out.push(fromDayNumber(d));
      }
    }
    return out;
  }

  // Only called for days that are already off, so an arife counts here exactly
  // when halfDays is "holiday".
  private isOffHoliday(n: number): boolean {
    return this.extraHolidays.has(n) || BY_DAY.has(n);
  }
}

/** The default calendar: five-day week, arife afternoons count as working days. */
export const DEFAULT = new Calendar();

export const holidays = (year: number): Holiday[] => DEFAULT.holidays(year);
export const holiday = (day: DateLike): Holiday | null => DEFAULT.holiday(day);
export const isHoliday = (day: DateLike): boolean => DEFAULT.isHoliday(day);
export const isBusinessDay = (day: DateLike): boolean => DEFAULT.isBusinessDay(day);
export const nextBusinessDay = (day: DateLike): string => DEFAULT.nextBusinessDay(day);
export const previousBusinessDay = (day: DateLike): string => DEFAULT.previousBusinessDay(day);
export const addBusinessDays = (day: DateLike, n: number): string =>
  DEFAULT.addBusinessDays(day, n);
export const businessDaysBetween = (start: DateLike, end: DateLike): number =>
  DEFAULT.businessDaysBetween(start, end);
export const deadline = (start: DateLike, days: number): string => DEFAULT.deadline(start, days);
export const bridgeDays = (year: number): string[] => DEFAULT.bridgeDays(year);
