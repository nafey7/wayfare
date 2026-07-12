import moment from "moment-timezone";
import {
  parsePhoneNumberWithError,
  formatIncompletePhoneNumber,
} from "libphonenumber-js";

export function calculatePercentageWithCondition(obj, condition) {
  const totalItems = Object.keys(obj).length;
  const filteredItems = Object.values(obj).filter(
    (value) => value === condition
  );
  const percentage = (filteredItems.length / totalItems) * 100;
  return percentage;
}
export function getSubscriptionDuration({
  startDate,
  endDate,
  tz,
  isReservation,
}) {
  // Directly create moments in the specified timezone
  const utcStart = moment.tz(startDate, tz);
  const utcEnd = moment.tz(endDate, tz);

  // Now, you can safely use startOf and endOf
  const startOfDate = utcStart
    // .startOf("day")
    .format(`MM/DD/YYYY ${isReservation ? "hh:mm A" : ""}`);
  const endOfDate = utcEnd
    // .endOf("day")
    .format(`MM/DD/YYYY ${isReservation ? "hh:mm A" : ""}`);

  const formattedDate = `${startOfDate} - ${endOfDate}`;
  return formattedDate;
}
export function getTimezoneName() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}
export function amountToShow(amount) {
  const formattedAmount = amount / 100;
  return `${formattedAmount.toFixed(2)}`;
}
export function getRandomEmoji() {
  const randomEmoji = ["🚀", "💫", "🤞🏻", "💕", "💥", "🔥"];
  const randomIndex = Math.floor(Math.random() * randomEmoji.length);
  return randomEmoji[randomIndex];
}
export function formatDateWithTimezone(date, tz) {
  const parsedDate = moment.tz(date, tz);
  const formattedDate = parsedDate.format("MM/DD/YYYY hh:mm A");
  return formattedDate;
}
export function mobileNumberMasking(number) {
  return formatIncompletePhoneNumber(number, "US") || number;
}
export function formattedDateWithTime(dateWithTime) {
  const createAt = moment(dateWithTime);
  const now = moment();
  const diff = now.diff(createAt, "minutes");
  const formattedDate = createAt.format("DD-MM-YYYY hh:mm A");

  let timeAgo;
  if (diff < 1) {
    timeAgo = "just now";
  } else if (diff < 60) {
    timeAgo = `${diff} minute${diff > 1 ? "s" : ""} ago`;
  } else if (diff < 1440) {
    const hours = Math.floor(diff / 60);
    timeAgo = `${hours} hour${hours > 1 ? "s" : ""} ago`;
  } else if (diff < 10080) {
    const days = Math.floor(diff / 1440);
    timeAgo = `${days} day${days > 1 ? "s" : ""} ago`;
  } else {
    timeAgo = formattedDate;
  }
  return timeAgo;
}

export function dollarsToCents(dollarAmount) {
  const res =
    typeof dollarAmount === "number" && !isNaN(dollarAmount)
      ? dollarAmount * 100
      : 0;
  return res;
}

export function centsToDollars(centsAmount) {
  const res =
    typeof centsAmount === "number" && !isNaN(centsAmount)
      ? centsAmount / 100
      : 0;
  return res;
}
export function capitalizeFirstLetter(str) {
  if (typeof str !== "string" || str.length === 0) {
    return str;
  }
  return str.charAt(0).toUpperCase() + str.slice(1);
}
