/**
 * Maps profile aggregate passengers to Travel Details UI shapes.
 * Backend uses YYYY-MM-DD; UI displays MM/DD/YYYY.
 */

import type { ProfileAggregate } from '@/types/profile';
import type { PersonalInfoData, PassportInfoData } from '@/features/profile/components/travelDetails/PersonalInformationSection';
import type { TravelCompanionData } from '@/features/profile/components/travelDetails/TravelCompanionsSection';

type ProfilePassenger = ProfileAggregate['passengers'][number];

const PLACEHOLDER = '—';

/** Format ISO date (YYYY-MM-DD) to display format (MM/DD/YYYY). */
export function formatDateForDisplay(isoDate: string | null | undefined): string {
  if (isoDate == null || isoDate.trim() === '') return PLACEHOLDER;
  const parts = isoDate.split('-');
  if (parts.length !== 3) return isoDate;
  const [, month, day] = parts;
  const year = parts[0];
  return `${month}/${day}/${year}`;
}

/** Build full legal name from title + firstName + lastName. */
function toFullLegalName(p: ProfilePassenger): string {
  const parts = [p.title, p.firstName, p.lastName].filter(Boolean);
  return parts.join(' ').trim() || PLACEHOLDER;
}

/** Map primary passenger to PersonalInfoData + PassportInfoData. */
export function passengerToPersonalInfo(
  p: ProfilePassenger | null | undefined
): { personalInfo: PersonalInfoData; passportInfo: PassportInfoData } {
  if (!p) {
    return {
      personalInfo: {
        fullLegalName: PLACEHOLDER,
        dateOfBirth: PLACEHOLDER,
        nationality: PLACEHOLDER,
      },
      passportInfo: {
        passportNumber: PLACEHOLDER,
        passportExpiryDate: PLACEHOLDER,
        countryOfIssue: PLACEHOLDER,
      },
    };
  }
  return {
    personalInfo: {
      fullLegalName: toFullLegalName(p),
      dateOfBirth: formatDateForDisplay(p.dateOfBirth),
      nationality: p.nationality?.trim() || PLACEHOLDER,
    },
    passportInfo: {
      passportNumber: p.passportNumber?.trim() || PLACEHOLDER,
      passportExpiryDate: formatDateForDisplay(p.passportExpiry),
      countryOfIssue: p.passportCountry?.trim() || PLACEHOLDER,
    },
  };
}

/** Extended companion data with id for CRUD operations. */
export interface TravelCompanionDataWithId extends TravelCompanionData {
  id: string;
}

/** Map passenger to TravelCompanionData (with id for edit/delete). */
export function passengerToCompanionData(p: ProfilePassenger): TravelCompanionDataWithId {
  const hasPassport = !!(p.passportNumber?.trim() || p.passportExpiry?.trim());
  return {
    id: p.id,
    fullLegalName: toFullLegalName(p),
    dateOfBirth: formatDateForDisplay(p.dateOfBirth),
    nationality: p.nationality?.trim() || PLACEHOLDER,
    hasPassport,
    type: p.type as 'adult' | 'child' | 'infant' | null,
    passportExpiry: p.passportExpiry ?? null,
  };
}
