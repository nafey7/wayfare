import { Box, Group, Stack, Text, UnstyledButton } from '@mantine/core';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';
import {
  useCreatePassengerMutation,
  useUpdatePassengerMutation,
  useGetProfileQuery,
  useRequestPiiVerificationMutation,
  useVerifyPiiOtpMutation,
  useLazyGetPassengerQuery,
} from '@/api/usersApi';
import {
  isMaskedPassportValue,
  isMaskedFrequentFlyerValue,
} from '@/features/flights/utils/passengerStorageUtils';
import type { PassengerCreateRequest } from '@/types/passengers';
import type { ProfileAggregate } from '@/types/profile';
import {
  passengerToPersonalInfo,
  passengerToCompanionData,
  type TravelCompanionDataWithId,
} from '@/features/profile/utils/passengerMappers';
import type { PassportInfoData } from './PersonalInformationSection';
import { PersonalInformationSection } from './PersonalInformationSection';
import { TravelCompanionsSection } from './TravelCompanionsSection';
import { CompanionFormView } from './CompanionFormView';
import { PassengerFormDialog } from './PassengerFormDialog';

type TravelDetailsTab = 'personalInfo' | 'travelCompanions';

/** null = list, 'add' = add form, string = edit passengerId */
type CompanionSub = null | 'add' | string;

const TABS: { id: TravelDetailsTab; label: string }[] = [
  { id: 'personalInfo', label: 'Personal Information' },
  { id: 'travelCompanions', label: 'Travel Companions' },
];

/** Matches backend PII_VIEW_TOKEN_EXPIRE_MINUTES - clear decrypted data when token would expire. */
const PII_VIEW_TIMEOUT_MS = 2 * 60 * 1000;

const tabChipStyle: React.CSSProperties = {
  height: 32,
  borderRadius: 8,
  paddingLeft: 12,
  paddingRight: 12,
  paddingTop: 6,
  paddingBottom: 6,
  minHeight: 0,
  margin: 0,
  fontSize: 14,
  fontWeight: 600,
  lineHeight: 1.43,
  fontFamily: LANDING_TOKENS.fontFamily.display,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
};

export interface TravelDetailsSectionProps {
  profile: ProfileAggregate | null | undefined;
}

/**
 * Travel details section — personal info, travel companions.
 * Companions use an inline form view (back button navigation); primary passenger uses a modal.
 */
export function TravelDetailsSection({ profile }: TravelDetailsSectionProps) {
  const [activeTab, setActiveTab] = useState<TravelDetailsTab>('personalInfo');
  const [companionSub, setCompanionSub] = useState<CompanionSub>(null);

  const [createPassenger] = useCreatePassengerMutation();
  const [updatePassenger] = useUpdatePassengerMutation();
  const [requestPiiVerification] = useRequestPiiVerificationMutation();
  const [verifyPiiOtp] = useVerifyPiiOtpMutation();
  const [getPassenger] = useLazyGetPassengerQuery();
  const { refetch } = useGetProfileQuery();

  const [piiChallengeId, setPiiChallengeId] = useState<string | null>(null);
  const [piiMaskedEmail, setPiiMaskedEmail] = useState<string | undefined>(undefined);
  const [decryptedPassportInfo, setDecryptedPassportInfo] = useState<PassportInfoData | null>(null);
  const clearPassportTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear decrypted passport after 2 min (matches token expiry) or when tab becomes hidden
  useEffect(() => {
    if (!decryptedPassportInfo) return;

    const clearPassport = () => {
      setDecryptedPassportInfo(null);
      if (clearPassportTimeoutRef.current) {
        clearTimeout(clearPassportTimeoutRef.current);
        clearPassportTimeoutRef.current = null;
      }
    };

    clearPassportTimeoutRef.current = setTimeout(clearPassport, PII_VIEW_TIMEOUT_MS);

    const onVisibilityChange = () => {
      if (document.hidden) clearPassport();
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      if (clearPassportTimeoutRef.current) clearTimeout(clearPassportTimeoutRef.current);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [decryptedPassportInfo]);

  const passengers = profile?.passengers ?? [];
  const primaryPassenger = passengers.find((p) => p.isPrimary) ?? passengers[0];
  const companions: TravelCompanionDataWithId[] = passengers
    .filter((p) => !p.isPrimary)
    .map(passengerToCompanionData);

  const { personalInfo, passportInfo: basePassportInfo } = useMemo(
    () => passengerToPersonalInfo(primaryPassenger),
    [primaryPassenger]
  );

  const passportInfo = decryptedPassportInfo ?? basePassportInfo;

  // Primary passenger modal state (companions use inline CompanionFormView instead)
  const [dialogMode, setDialogMode] = useState<'add' | 'edit' | null>(null);
  const [editingPassengerId, setEditingPassengerId] = useState<string | null>(null);

  const maskEmail = (email: string | null | undefined): string | undefined => {
    if (!email?.trim()) return undefined;
    const [local, domain] = email.split('@');
    if (!domain) return email;
    const masked = local?.length ? `${local[0]}***` : '***';
    return `${masked}@${domain}`;
  };

  const maskedEmail = piiMaskedEmail ?? maskEmail(profile?.user?.email ?? primaryPassenger?.email);

  const handleViewPassport = useCallback(
    async (method: 'email' | 'sms' | 'authenticator') => {
      if (method !== 'email') return;
      try {
        const res = await requestPiiVerification().unwrap();
        setPiiChallengeId(res.challengeId);
        setPiiMaskedEmail(res.maskedEmail);
      } catch (err) {
        console.error('PII verification request failed:', err);
      }
    },
    [requestPiiVerification]
  );

  const handleVerifyCode = useCallback(
    async (code: string) => {
      if (!piiChallengeId || !primaryPassenger?.id) return;
      try {
        const { piiViewToken } = await verifyPiiOtp({
          challengeId: piiChallengeId,
          code,
        }).unwrap();
        const decrypted = await getPassenger({
          passengerId: primaryPassenger.id,
          includeSensitive: true,
          piiViewToken,
        }).unwrap();
        const { passportInfo: decryptedPassport } = passengerToPersonalInfo(decrypted);
        setDecryptedPassportInfo(decryptedPassport);
        setPiiChallengeId(null);
      } catch (err) {
        console.error('PII verification failed:', err);
        throw err;
      }
    },
    [piiChallengeId, primaryPassenger?.id, verifyPiiOtp, getPassenger]
  );

  const handleCreatePrimary = useCallback(
    async (data: PassengerCreateRequest) => {
      await createPassenger({ ...data, isPrimary: true } as PassengerCreateRequest & {
        isPrimary?: boolean;
      }).unwrap();
      await refetch();
      setDialogMode(null);
    },
    [createPassenger, refetch]
  );

  const handleUpdate = useCallback(
    async (data: PassengerCreateRequest) => {
      const id = editingPassengerId;
      if (!id) return;
      const body: Parameters<typeof updatePassenger>[0]['body'] = {
        title: data.title,
        firstName: data.firstName,
        lastName: data.lastName,
        dateOfBirth: data.dateOfBirth,
        nationality: data.nationality,
        email: data.email,
        phone: data.phone,
        type: data.type,
        isPrimary: data.isPrimary,
      };
      if (!isMaskedPassportValue(data.passportNumber, 'number'))
        body.passportNumber = data.passportNumber;
      if (!isMaskedPassportValue(data.passportExpiry, 'expiry'))
        body.passportExpiry = data.passportExpiry;
      if (!isMaskedFrequentFlyerValue(data.frequentFlyerNumber))
        body.frequentFlyerNumber = data.frequentFlyerNumber;
      if (data.passportCountry) body.passportCountry = data.passportCountry;
      await updatePassenger({ passengerId: id, body }).unwrap();
      await refetch();
      setDialogMode(null);
      setEditingPassengerId(null);
    },
    [editingPassengerId, updatePassenger, refetch]
  );

  const editingPassenger = editingPassengerId
    ? passengers.find((p) => p.id === editingPassengerId)
    : null;

  const handleEditPrimary = useCallback(() => {
    setEditingPassengerId(primaryPassenger?.id ?? null);
    setDialogMode('edit');
  }, [primaryPassenger]);

  const handleOpenCreatePrimary = useCallback(() => {
    setEditingPassengerId(null);
    setDialogMode('add');
  }, []);

  const handleTabChange = useCallback((tab: TravelDetailsTab) => {
    setActiveTab(tab);
    setCompanionSub(null);
  }, []);

  const renderContent = () => {
    switch (activeTab) {
      case 'personalInfo':
        return (
          <PersonalInformationSection
            personalInfo={personalInfo}
            passportInfo={passportInfo}
            maskedEmail={maskedEmail}
            passengerId={primaryPassenger?.id}
            onEdit={primaryPassenger ? handleEditPrimary : undefined}
            onAdd={!primaryPassenger ? handleOpenCreatePrimary : undefined}
            onViewPassport={handleViewPassport}
            onVerifyCode={handleVerifyCode}
          />
        );
      case 'travelCompanions':
        if (companionSub !== null) {
          return (
            <CompanionFormView
              passengerId={companionSub === 'add' ? undefined : companionSub}
              onBack={() => setCompanionSub(null)}
              onSuccess={() => { void refetch(); }}
            />
          );
        }
        return (
          <TravelCompanionsSection
            companions={companions}
            onAdd={() => setCompanionSub('add')}
            onEdit={(passengerId) => setCompanionSub(passengerId)}
          />
        );
    }
  };

  return (
    <>
      <Stack gap={0}>
        <Text
          component="span"
          style={{
            flex: 1,
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.29,
            color: LANDING_TOKENS.textColor,
            margin: 0,
            display: 'block',
            fontFamily: LANDING_TOKENS.fontFamily.display,
            padding: '10px 16px',
          }}
        >
          Travel Details
        </Text>
        <Group gap={12} px="md">
          {TABS.map(({ id, label }) => {
            const selected = activeTab === id;
            return (
              <UnstyledButton
                key={id}
                onClick={() => handleTabChange(id)}
                style={{
                  ...tabChipStyle,
                  ...(selected
                    ? {
                        backgroundColor: LANDING_TOKENS.baseColor,
                        color: LANDING_TOKENS.textLight,
                      }
                    : {
                        border: '1px solid var(--mantine-color-default-border)',
                        color: LANDING_TOKENS.textHighlight,
                        backgroundColor: 'transparent',
                      }),
                }}
              >
                {label}
              </UnstyledButton>
            );
          })}
        </Group>

        <Box
          mt={31}
          style={{
            border: `1px solid ${LANDING_TOKENS.baseLighter}`,
            borderRadius: 25,
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 31,
            backgroundColor: 'white',
          }}
        >
          {renderContent()}
        </Box>
      </Stack>

      {/* Primary passenger modal — companions use inline CompanionFormView */}
      <PassengerFormDialog
        open={dialogMode === 'add' || dialogMode === 'edit'}
        onClose={() => {
          setDialogMode(null);
          setEditingPassengerId(null);
        }}
        onSubmit={dialogMode === 'edit' ? handleUpdate : handleCreatePrimary}
        initialData={editingPassenger ?? undefined}
        isUpdate={dialogMode === 'edit'}
      />
    </>
  );
}
