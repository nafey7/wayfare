import {
  ActionIcon,
  Box,
  Button,
  Group,
  Modal,
  PinInput,
  Radio,
  Stack,
  Text,
  UnstyledButton,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { Eye, Mail, Pencil, PlusCircle } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { LANDING_TOKENS } from '@/features/landing/landingTokens';

/** Extract API error detail from unknown error (Axios-style { data: { detail } }). */
function getApiErrorDetail(err: unknown): string | undefined {
  if (typeof err !== 'object' || err === null || !('data' in err)) return undefined;
  const data = (err as { data?: { detail?: string } }).data;
  return typeof data?.detail === 'string' ? data.detail : undefined;
}

/**
 * Verification method for passport view.
 *
 * NOTE: only `'email'` is offered in the picker today (`VerifyIdentityDialog`
 * options array). The `'sms'` / `'authenticator'` variants exist as future
 * work — `maskedDestination` already routes them — but the picker renders
 * only the email option until those backends are implemented.
 */
export type VerificationMethod = 'email' | 'sms' | 'authenticator';

function VerifyIdentityDialog({
  open,
  onClose,
  onContinue,
  maskedEmail,
}: {
  open: boolean;
  onClose: () => void;
  onContinue: (method: VerificationMethod) => void;
  maskedEmail?: string;
}) {
  const [selected, setSelected] = useState<VerificationMethod>('email');

  const handleContinue = useCallback(() => {
    onContinue(selected);
    onClose();
  }, [selected, onContinue, onClose]);

  const options: { value: VerificationMethod; label: string; sublabel: string }[] = [
    { value: 'email', label: 'Email', sublabel: `Send code to ${maskedEmail ?? 'j***@gmail.com'}` },
  ];

  return (
    <Modal opened={open} onClose={onClose} centered radius="md" size="md" withCloseButton={false}>
      <Stack gap={0}>
        <Stack align="center" py="md" gap="md">
          <Text
            component="span"
            style={{
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 28 / 22,
              color: LANDING_TOKENS.textColor,
              textAlign: 'center',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            Verify your identity
          </Text>
          <Text
            component="span"
            style={{
              fontSize: 14,
              fontWeight: 400,
              lineHeight: 18 / 14,
              letterSpacing: 0.1,
              color: LANDING_TOKENS.textColor,
              textAlign: 'center',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            To view sensitive passport information
          </Text>
        </Stack>

        <Radio.Group value={selected} onChange={(v) => setSelected(v as VerificationMethod)}>
          <Stack gap="xs">
            {options.map((opt) => (
              <UnstyledButton
                key={opt.value}
                onClick={() => setSelected(opt.value)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  minHeight: 48,
                  borderRadius: 4,
                  border: `1px solid ${LANDING_TOKENS.baseLighter}`,
                  backgroundColor: 'white',
                  cursor: 'pointer',
                  textAlign: 'left',
                  paddingTop: 10,
                  paddingBottom: 10,
                  paddingLeft: 16,
                  paddingRight: 16,
                  gap: 16,
                }}
              >
                <Mail size={24} color={LANDING_TOKENS.textHighlight} />
                <Box style={{ flex: 1 }}>
                  <Text
                    component="span"
                    style={{
                      fontSize: 16,
                      fontWeight: 600,
                      lineHeight: '20px',
                      color: LANDING_TOKENS.textColor,
                      fontFamily: LANDING_TOKENS.fontFamily.display,
                      display: 'block',
                    }}
                  >
                    {opt.label}
                  </Text>
                  <Text
                    component="span"
                    style={{
                      fontSize: 14,
                      fontWeight: 400,
                      lineHeight: '18px',
                      letterSpacing: 0.1,
                      color: LANDING_TOKENS.textHighlight,
                      fontFamily: LANDING_TOKENS.fontFamily.display,
                      display: 'block',
                      marginTop: 2,
                    }}
                  >
                    {opt.sublabel}
                  </Text>
                </Box>
                <Radio value={opt.value} size="sm" color="brand.6" />
              </UnstyledButton>
            ))}
          </Stack>
        </Radio.Group>

        <Group justify="flex-end" gap="xs" mt="md">
          <Button variant="subtle" tt="none" fw={600} onClick={onClose} c={LANDING_TOKENS.textColor}>
            Cancel
          </Button>
          <Button
            onClick={handleContinue}
            radius={100}
            tt="none"
            fw={600}
            style={{
              backgroundColor: LANDING_TOKENS.baseColor,
              color: LANDING_TOKENS.textLight,
            }}
          >
            Continue
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function EnterVerificationCodeDialog({
  open,
  onClose,
  onVerify,
  onResend,
  maskedDestination,
}: {
  open: boolean;
  onClose: () => void;
  onVerify: (code: string) => void | Promise<void>;
  onResend: () => void;
  maskedDestination: string;
}) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isComplete = code.length === 6;

  useEffect(() => {
    if (open) {
      setCode('');
      setError(null);
    }
  }, [open]);

  const handleVerify = useCallback(async () => {
    if (!isComplete) return;
    setError(null);
    setLoading(true);
    try {
      await Promise.resolve(onVerify(code));
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Verification failed. Please try again.';
      setError(getApiErrorDetail(err) ?? msg);
    } finally {
      setLoading(false);
    }
  }, [isComplete, code, onVerify]);

  return (
    <Modal opened={open} onClose={onClose} centered radius="md" size="md" withCloseButton={false}>
      <Stack gap={0}>
        <Stack align="center" py="md" gap="md">
          <Text
            component="span"
            style={{
              fontSize: 22,
              fontWeight: 700,
              lineHeight: 28 / 22,
              color: LANDING_TOKENS.textColor,
              textAlign: 'center',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            Verify your identity
          </Text>
          <Text
            component="span"
            style={{
              fontSize: 14,
              fontWeight: 400,
              lineHeight: 18 / 14,
              letterSpacing: 0.1,
              color: LANDING_TOKENS.textColor,
              textAlign: 'center',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            To view sensitive passport information
          </Text>
        </Stack>

        <Stack align="center" gap="md">
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              lineHeight: 16 / 12,
              letterSpacing: 0.1,
              color: LANDING_TOKENS.textHighlight,
              textAlign: 'center',
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            We sent a 6-digit code to {maskedDestination}
          </Text>
          {error && (
            <Text c="red" size="sm" ta="center">
              {error}
            </Text>
          )}
          <PinInput
            length={6}
            value={code}
            onChange={setCode}
            type="number"
            inputMode="numeric"
            size="lg"
            radius="sm"
          />
          <Group gap={4} align="center">
            <Text
              component="span"
              style={{
                fontSize: 12,
                fontWeight: 600,
                lineHeight: 16 / 12,
                letterSpacing: 0.1,
                color: LANDING_TOKENS.textHighlight,
                fontFamily: LANDING_TOKENS.fontFamily.display,
              }}
            >
              Didn&apos;t receive it?
            </Text>
            <UnstyledButton
              onClick={onResend}
              style={{
                fontSize: 12,
                fontWeight: 600,
                lineHeight: 16 / 12,
                letterSpacing: 0.1,
                color: LANDING_TOKENS.baseColor,
                fontFamily: LANDING_TOKENS.fontFamily.display,
              }}
            >
              Resend Code
            </UnstyledButton>
          </Group>
        </Stack>

        <Group justify="flex-end" gap="xs" mt="md">
          <Button variant="subtle" tt="none" fw={600} onClick={onClose} c={LANDING_TOKENS.textColor}>
            Cancel
          </Button>
          <Button
            onClick={handleVerify}
            disabled={!isComplete || loading}
            radius={100}
            tt="none"
            fw={600}
            style={{
              backgroundColor: LANDING_TOKENS.baseColor,
              color: LANDING_TOKENS.textLight,
            }}
          >
            {loading ? 'Verifying…' : 'Verify'}
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}

function LocalSectionHeader({
  label,
  action,
}: {
  label: string;
  action?: React.ReactNode;
}) {
  return (
    <Group justify="space-between" align="center" pb={10}>
      <Text
        component="span"
        style={{
          fontSize: 18,
          fontWeight: 700,
          lineHeight: 25 / 18,
          letterSpacing: 0.15,
          color: LANDING_TOKENS.textColor,
          margin: 0,
          display: 'block',
          fontFamily: LANDING_TOKENS.fontFamily.display,
        }}
      >
        {label}
      </Text>
      {action}
    </Group>
  );
}

function PassportSectionHeader({ onView }: { onView?: () => void }) {
  return (
    <Group gap={12} pb={10} align="center" style={{ fontFamily: LANDING_TOKENS.fontFamily.display }}>
      <Text
        component="span"
        style={{
          fontSize: 18,
          fontWeight: 700,
          lineHeight: 25 / 18,
          letterSpacing: 0.15,
          color: LANDING_TOKENS.textColor,
          margin: 0,
          display: 'block',
          fontFamily: LANDING_TOKENS.fontFamily.display,
        }}
      >
        Passport Information
      </Text>
      {onView && (
        <UnstyledButton
          onClick={onView}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            height: 28,
            borderRadius: 4,
            backgroundColor: 'var(--mantine-color-gray-2)',
            color: 'var(--mantine-color-dark-8)',
            fontFamily: LANDING_TOKENS.fontFamily.display,
            fontWeight: 600,
            fontSize: 12,
            lineHeight: 16 / 12,
            letterSpacing: 0.1,
            paddingLeft: 8,
            paddingRight: 12,
            cursor: 'pointer',
          }}
        >
          <Eye size={14} />
          View
        </UnstyledButton>
      )}
    </Group>
  );
}

interface InfoRowProps {
  overline: string;
  value: string;
}

function InfoRow({ overline, value }: InfoRowProps) {
  return (
    <Box
      style={{
        minHeight: 48,
        paddingTop: 10,
        paddingBottom: 10,
        borderBottom: `1px solid ${LANDING_TOKENS.borderLight}`,
      }}
    >
      <Text
        component="span"
        style={{
          fontSize: 12,
          fontWeight: 600,
          lineHeight: 16 / 12,
          letterSpacing: 0.1,
          color: LANDING_TOKENS.textHighlight,
          margin: 0,
          display: 'block',
          fontFamily: LANDING_TOKENS.fontFamily.display,
        }}
      >
        {overline}
      </Text>
      <Text
        component="span"
        style={{
          fontSize: 16,
          fontWeight: 600,
          lineHeight: 20 / 16,
          color: LANDING_TOKENS.textColor,
          margin: 0,
          display: 'block',
          marginTop: 2,
          fontFamily: LANDING_TOKENS.fontFamily.display,
        }}
      >
        {value}
      </Text>
    </Box>
  );
}

export interface PersonalInfoData {
  fullLegalName: string;
  dateOfBirth: string;
  nationality: string;
}

export interface PassportInfoData {
  passportNumber: string;
  passportExpiryDate: string;
  countryOfIssue: string;
}

const PLACEHOLDER = '—';

export interface PersonalInformationSectionProps {
  personalInfo?: PersonalInfoData;
  passportInfo?: PassportInfoData;
  /** Masked email for verification dialog. */
  maskedEmail?: string;
  /** Masked phone for verification dialog when method is SMS. */
  maskedPhone?: string;
  /** Passenger id (for edit flow). */
  passengerId?: string;
  /** Called when user clicks Edit. */
  onEdit?: () => void;
  /** Called when user clicks Add — for empty state. */
  onAdd?: () => void;
  /** Called when user selects a verification method and clicks Continue. */
  onViewPassport?: (method: VerificationMethod) => void | Promise<void>;
  /** Called when user enters the 6-digit code and clicks Verify. Throws on failure. */
  onVerifyCode?: (code: string) => void | Promise<void>;
}

const DEFAULT_PERSONAL: PersonalInfoData = {
  fullLegalName: 'John Doe',
  dateOfBirth: '05/16/1987',
  nationality: 'United States',
};

const DEFAULT_PASSPORT: PassportInfoData = {
  passportNumber: '*************',
  passportExpiryDate: '**/**/**',
  countryOfIssue: 'Spain',
};

/**
 * Personal Information section — passenger and passport details within Travel details.
 * View button opens Verify Identity dialog.
 */
export function PersonalInformationSection({
  personalInfo = DEFAULT_PERSONAL,
  passportInfo = DEFAULT_PASSPORT,
  maskedEmail,
  maskedPhone,
  passengerId,
  onEdit,
  onAdd,
  onViewPassport,
  onVerifyCode,
}: PersonalInformationSectionProps) {
  const isMdUp = useMediaQuery('(min-width: 900px)') ?? false;
  const [verifyDialogOpen, setVerifyDialogOpen] = useState(false);
  const [enterCodeDialogOpen, setEnterCodeDialogOpen] = useState(false);
  const [selectedVerificationMethod, setSelectedVerificationMethod] =
    useState<VerificationMethod>('email');

  const handleViewClick = useCallback(() => {
    setVerifyDialogOpen(true);
  }, []);

  const handleVerifyContinue = useCallback(
    (method: VerificationMethod) => {
      setSelectedVerificationMethod(method);
      setVerifyDialogOpen(false);
      onViewPassport?.(method);
      setEnterCodeDialogOpen(true);
    },
    [onViewPassport]
  );

  const maskedDestination =
    selectedVerificationMethod === 'email'
      ? maskedEmail ?? 'j***@gmail.com'
      : selectedVerificationMethod === 'sms'
        ? maskedPhone ?? '+1 ••• •••4821'
        : 'your authenticator app';

  const handleVerifyCode = useCallback(
    async (code: string) => {
      await onVerifyCode?.(code);
      setEnterCodeDialogOpen(false);
    },
    [onVerifyCode]
  );

  const handleResendCode = useCallback(() => {
    onViewPassport?.(selectedVerificationMethod);
  }, [onViewPassport, selectedVerificationMethod]);

  const isEmpty = personalInfo.fullLegalName === PLACEHOLDER;
  const passengerAction =
    !isEmpty && onEdit && passengerId ? (
      <ActionIcon size="md" onClick={onEdit} aria-label="Edit" variant="subtle" color="gray">
        <Pencil size={20} />
      </ActionIcon>
    ) : undefined;

  return (
    <Stack
      gap={isMdUp ? 32 : 24}
      style={{ flexDirection: isMdUp ? 'row' : 'column', justifyContent: 'space-between', width: '100%' }}
    >
      <Box style={{ flex: 1, minWidth: 0 }}>
        {!isEmpty && <LocalSectionHeader label="Passenger Information" action={passengerAction} />}
        {isEmpty && onAdd ? (
          <UnstyledButton
            onClick={onAdd}
            style={{
              width: '100%',
              border: `1px solid ${LANDING_TOKENS.baseLighter}`,
              borderRadius: 16,
              padding: 16,
              minWidth: 0,
              cursor: 'pointer',
              backgroundColor: 'transparent',
              textAlign: 'left',
            }}
          >
            <Group gap={12} align="center">
              <PlusCircle size={24} color={LANDING_TOKENS.baseColor} />
              <Text
                component="span"
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  lineHeight: 20 / 16,
                  color: LANDING_TOKENS.baseColor,
                  margin: 0,
                  display: 'block',
                  fontFamily: LANDING_TOKENS.fontFamily.display,
                }}
              >
                Add
              </Text>
            </Group>
          </UnstyledButton>
        ) : isEmpty && !onAdd ? null : (
          <Stack gap={0}>
            <InfoRow overline="Full Legal Name" value={personalInfo.fullLegalName} />
            <InfoRow overline="Date of Birth" value={personalInfo.dateOfBirth} />
            <InfoRow overline="Nationality" value={personalInfo.nationality} />
          </Stack>
        )}
      </Box>

      {!isEmpty && (
        <Box style={{ flex: 1, minWidth: 0 }}>
          <PassportSectionHeader onView={onViewPassport ? handleViewClick : undefined} />
          <Stack gap={0}>
            <InfoRow overline="Passport Number" value={passportInfo.passportNumber} />
            <InfoRow overline="Passport expiry date" value={passportInfo.passportExpiryDate} />
            <InfoRow overline="Country of issue" value={passportInfo.countryOfIssue} />
          </Stack>
          <Text
            component="span"
            style={{
              fontSize: 11,
              fontWeight: 600,
              lineHeight: 14 / 11,
              letterSpacing: 0.2,
              color: LANDING_TOKENS.textColor,
              margin: 0,
              display: 'block',
              marginTop: 12,
              fontFamily: LANDING_TOKENS.fontFamily.display,
            }}
          >
            Stored securely and only used when completing bookings.
          </Text>
        </Box>
      )}

      <VerifyIdentityDialog
        open={verifyDialogOpen}
        onClose={() => setVerifyDialogOpen(false)}
        onContinue={handleVerifyContinue}
        maskedEmail={maskedEmail}
      />

      <EnterVerificationCodeDialog
        open={enterCodeDialogOpen}
        onClose={() => setEnterCodeDialogOpen(false)}
        onVerify={handleVerifyCode}
        onResend={handleResendCode}
        maskedDestination={maskedDestination}
      />
    </Stack>
  );
}
