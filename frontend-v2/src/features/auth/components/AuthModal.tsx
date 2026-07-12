import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { zIndex } from '@/theme';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  ActionIcon,
  Alert,
  Box,
  Button,
  Group,
  Modal,
  PasswordInput,
  Progress,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useMediaQuery } from '@mantine/hooks';
import { X } from 'lucide-react';
import {
  useCheckEmailMutation,
  useRegisterMutation,
  useLoginMutation,
} from '@/api';
import { useAppDispatch, useAppSelector } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';
import { setPublicChatPendingCompleteRegistration } from '@/features/chat/utils/publicChatSignupIntent';
import {
  clearPublicChatReturnTo,
  stashPublicChatReturnTo,
} from '@/features/chat/utils/publicChatReturnRoute';
import {
  isPublicChatContentRoute,
  isPublicChatRoute,
  publicToAuthRoute,
} from '@/features/routing/constants';
import { trackEvent } from '@/utils/gtm';
import { getRedirectToChatAfterAuth, type RedirectCheckResult } from '@/features/auth/utils/authRedirectUtils';
import { useChatContext } from '@/features/chat';
import {
  clearPostAuthOnboardingPath,
  consumePostAuthOnboardingPath,
} from '@/features/onboarding/utils/postAuthOnboardingPath';
import { navBarAuthCtaButtonStyles } from '@/features/landing/components/navbarAuthCtaStyles';
import { GoogleAuthButton } from './GoogleAuthButton';

// Validation schemas
const emailSchema = z.object({
  email: z.string().email('Invalid email address'),
});

const registrationSchema = z.object({
  email: z.string().email('Invalid email address'),
  firstName: z
    .string()
    .min(1, 'First name is required')
    .max(50, 'First name must be less than 50 characters'),
  lastName: z
    .string()
    .min(1, 'Last name is required')
    .max(50, 'Last name must be less than 50 characters'),
});

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters'),
});

type Step = 'email' | 'registration' | 'login';
type AlertSeverity = 'success' | 'error' | 'warning' | 'info';

interface AuthModalProps {
  open: boolean;
  onClose: () => void;
}

// Glassmorphism text-field styles for Mantine TextInput / PasswordInput.
// Mantine takes a per-slot `styles` object instead of MUI's nested sx selectors.
// The `&:-webkit-autofill` transition disables Chrome's autofill repaint so
// saved-email autofills don't overwrite the transparent background; this was
// in the MUI version and is required to keep the glassmorphism intact.
const textFieldStyles = {
  input: {
    backgroundColor: 'transparent',
    color: '#ffffff',
    borderColor: '#ffffff',
    borderRadius: '8px',
    '&::placeholder': { color: 'rgba(255,255,255,0.6)' },
    '&:focus': { borderColor: '#ffffff' },
    '&:-webkit-autofill': {
      transition: 'background-color 600000s 0s, color 600000s 0s',
    },
    '&:disabled': {
      borderColor: 'rgba(255, 255, 255, 0.5)',
      color: 'rgba(255, 255, 255, 0.7)',
      opacity: 1,
    },
  },
  label: { color: 'white' },
  description: { color: 'rgba(255,255,255,0.7)' },
} as const;

export function AuthModal({ open, onClose }: AuthModalProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const chatConfig = useAppSelector(selectChatConfig);
  const configLoaded = useAppSelector(selectConfigLoaded);
  const { openChat } = useChatContext();
  // Stack registration first/last name vertically below the sm breakpoint
  // (matches the MUI `Stack direction={{ xs: 'column', sm: 'row' }}` original).
  const isSmUp = useMediaQuery('(min-width: 48em)');
  const modalLayout = isSmUp
    ? { size: 'md' as const, bodyPadding: '4px 32px 18px' }
    : { size: 'sm' as const, bodyPadding: '0px 24px 10px' };

  const [step, setStep] = useState<Step>('email');
  const [alert, setAlert] = useState<{ message: string; severity: AlertSeverity } | null>(null);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  const [checkEmail, { isLoading: isCheckingEmail }] = useCheckEmailMutation();
  const [registerUser, { isLoading: isRegistering }] = useRegisterMutation();
  const [login, { isLoading: isLoggingIn }] = useLoginMutation();

  const isLoading = isCheckingEmail || isRegistering || isLoggingIn;

  // Forms
  const emailForm = useForm({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: '' },
  });

  const registrationForm = useForm({
    resolver: zodResolver(registrationSchema),
    defaultValues: { email: '', firstName: '', lastName: '' },
  });

  const loginForm = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const handleClose = () => {
    clearPostAuthOnboardingPath();
    onClose();
    setStep('email');
    setAlert(null);
    setRegistrationSuccess(false);
    emailForm.reset();
    registrationForm.reset();
    loginForm.reset();
  };

  const handleEmailSubmit = async (data: { email: string }) => {
    setAlert(null);
    try {
      const result = await checkEmail({ email: data.email }).unwrap();

      if (!result.exists) {
        setStep('registration');
        registrationForm.setValue('email', data.email);
        setAlert({
          message: 'Please enter your details to complete registration.',
          severity: 'info',
        });
      } else if (result.verified) {
        setStep('login');
        loginForm.setValue('email', data.email);
        setAlert({
          message: 'Welcome back! Please enter your password.',
          severity: 'info',
        });
      } else {
        // Unverified user: backend auto-resends registration email
        setAlert({
          message: result.message,
          severity: 'success',
        });
        setStep('email'); // Stay on email step; user can close modal
      }
    } catch {
      setAlert({
        message: 'Something went wrong. Please try again.',
        severity: 'error',
      });
    }
  };

  const handleRegistrationSubmit = async (data: { email: string; firstName: string; lastName: string }) => {
    setAlert(null);
    try {
      await registerUser({
        email: data.email,
        first_name: data.firstName,
        last_name: data.lastName,
      }).unwrap();
      // Tab A → Tab B: stash authenticated equivalent path for post-verification navigation.
      if (isPublicChatContentRoute(location.pathname)) {
        stashPublicChatReturnTo(publicToAuthRoute(location.pathname), location.search);
      }
      // Pending handoff: config may still be loading — still set when URL is a public chat surface.
      if (
        (configLoaded && chatConfig.publicChatEnabled) ||
        isPublicChatRoute(location.pathname)
      ) {
        setPublicChatPendingCompleteRegistration();
      }
      trackEvent('user_registered', { method: 'email', email: data.email });
      setRegistrationSuccess(true);
      setAlert({
        message: 'Registration initiated. Please check your email to complete setup.',
        severity: 'success',
      });
    } catch {
      setAlert({
        message: 'Registration failed. Please try again.',
        severity: 'error',
      });
    }
  };

  const handleLoginSubmit = async (data: { email: string; password: string }) => {
    setAlert(null);
    try {
      const result = await login(data).unwrap();
      const redirectResult = getRedirectToChatAfterAuth();
      dispatch(setCredentials(result));
      if (isPublicChatRoute(location.pathname)) {
        clearPublicChatReturnTo();
      }
      trackEvent('user_login', { method: 'email', email: data.email });
      setAlert({
        message: 'Login successful!',
        severity: 'success',
      });
      const onboardingPath = consumePostAuthOnboardingPath();
      handleClose();
      if (redirectResult.redirect === 'chat') {
        navigate(`/chat?prompt=${encodeURIComponent(redirectResult.prompt)}`);
        return;
      }
      if (onboardingPath) {
        navigate(onboardingPath);
        return;
      }
      openChat();
    } catch {
      trackEvent('user_login_failed', {
        method: 'email',
        error: 'Login failed',
        email: data.email,
      });
      setAlert({
        message: 'Login failed. Please try again.',
        severity: 'error',
      });
    }
  };

  const handleForgotPassword = () => {
    handleClose();
    navigate('/forgot-password');
  };

  const titleByStep =
    step === 'email' ? 'Login' : step === 'registration' ? 'Create Account' : 'Welcome Back';

  return (
    <Modal
      opened={open}
      onClose={handleClose}
      size={modalLayout.size}
      withCloseButton={false}
      centered
      zIndex={zIndex.authModal}
      styles={{
        content: {
          background: 'linear-gradient(to bottom, rgba(122, 130, 208, 0.4), rgba(122, 130, 208, 0.2))',
          backdropFilter: 'blur(10px) saturate(180%)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)',
        },
        body: { padding: modalLayout.bodyPadding },
      }}
      radius="lg"
    >
      {/* Modal.Body already provides 24 px horizontal padding via styles.body;
          this row only needs vertical padding to align with the form inputs. */}
      <Group justify="space-between" align="center" py="md">
        <Title order={5} fz="1.5rem" fw="bold" c="white">
          {titleByStep}
        </Title>
        <ActionIcon
          variant="subtle"
          aria-label="close"
          onClick={handleClose}
          c="white"
          styles={{ root: { '&:hover': { backgroundColor: 'rgba(255, 255, 255, 0.1)' } } }}
        >
          <X size={18} />
        </ActionIcon>
      </Group>

      {isLoading && <Progress value={100} size="xs" striped animated />}

      <Box>
        {alert && (
          <Box mb="xs">
            <Alert
              withCloseButton
              onClose={() => setAlert(null)}
              color={
                alert.severity === 'error'
                  ? 'red'
                  : alert.severity === 'success'
                    ? 'green'
                    : alert.severity === 'warning'
                      ? 'yellow'
                      : 'blue'
              }
              variant="filled"
              radius="md"
            >
              {alert.message}
            </Alert>
          </Box>
        )}

        {/* Email Step */}
        {step === 'email' && (
          <Box component="form" onSubmit={emailForm.handleSubmit(handleEmailSubmit)}>
            <Text c="white" mb="sm">
              Enter your email to continue with Voya.
            </Text>
            <TextInput
              {...emailForm.register('email')}
              size="sm"
              label="Email Address"
              type="email"
              error={emailForm.formState.errors.email?.message}
              disabled={isLoading}
              styles={textFieldStyles}
            />
            <Stack pt="lg" pb="sm" gap="sm">
              <Group gap="sm" w="100%" justify="space-between" wrap="nowrap">
                <Button onClick={handleClose} variant="subtle" c="white" style={{ flex: 1, maxWidth: 120 }}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={isLoading}
                  style={{ flex: 2 }}
                  styles={{ root: navBarAuthCtaButtonStyles }}
                >
                  Continue
                </Button>
              </Group>

              <Group gap="sm" w="100%" align="center">
                <Box style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.3)' }} />
                <Text size="sm" c="white" style={{ opacity: 0.7 }}>
                  or
                </Text>
                <Box style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.3)' }} />
              </Group>

              <GoogleAuthButton
                disabled={isLoading}
                onSuccess={(result?: RedirectCheckResult) => {
                  if (isPublicChatRoute(location.pathname)) {
                    clearPublicChatReturnTo();
                  }
                  const redirectResult = result ?? getRedirectToChatAfterAuth();
                  const onboardingPath = consumePostAuthOnboardingPath();
                  handleClose();
                  if (redirectResult.redirect === 'chat') {
                    navigate(`/chat?prompt=${encodeURIComponent(redirectResult.prompt)}`);
                    return;
                  }
                  if (onboardingPath) {
                    navigate(onboardingPath);
                    return;
                  }
                  openChat();
                }}
              />
            </Stack>
          </Box>
        )}

        {/* Registration Step */}
        {step === 'registration' && (
          <>
            {registrationSuccess ? (
              <Box py="sm">
                <Text c="white" mb="lg">
                  Check your email and click the link to set your password and complete
                  signup. Didn&apos;t receive it? Re-open this modal and enter your email
                  again to resend.
                </Text>
                <Button fullWidth onClick={handleClose} mt="sm">
                  Got it
                </Button>
              </Box>
            ) : (
              <Box component="form" onSubmit={registrationForm.handleSubmit(handleRegistrationSubmit)}>
                <Text c="white" mb="sm">
                  Complete your registration to get started with Voya.
                </Text>
                <Stack gap="sm">
                  <TextInput
                    {...registrationForm.register('email')}
                    size="sm"
                    label="Email Address"
                    disabled
                    styles={textFieldStyles}
                  />
                  {(() => {
                    // Render firstName/lastName once; layout switches at sm:
                    // side-by-side on desktop, stacked on mobile.
                    const nameInputs = (
                      <>
                        <TextInput
                          {...registrationForm.register('firstName')}
                          size="sm"
                          label="First Name"
                          error={registrationForm.formState.errors.firstName?.message}
                          disabled={isLoading}
                          styles={textFieldStyles}
                        />
                        <TextInput
                          {...registrationForm.register('lastName')}
                          size="sm"
                          label="Last Name"
                          error={registrationForm.formState.errors.lastName?.message}
                          disabled={isLoading}
                          styles={textFieldStyles}
                        />
                      </>
                    );
                    return isSmUp ? (
                      <Group gap="sm" grow>
                        {nameInputs}
                      </Group>
                    ) : (
                      nameInputs
                    );
                  })()}
                </Stack>
                <Group gap="sm" w="100%" justify="space-between" wrap="nowrap" pt="lg" pb="sm">
                  <Button
                    onClick={() => setStep('email')}
                    variant="subtle"
                    c="white"
                    disabled={isLoading}
                    style={{ flex: 1, maxWidth: 120 }}
                  >
                    Back
                  </Button>
                  <Button
                    type="submit"
                    loading={isLoading}
                    style={{ flex: 2 }}
                    styles={{ root: navBarAuthCtaButtonStyles }}
                  >
                    Complete Registration
                  </Button>
                </Group>
              </Box>
            )}
          </>
        )}

        {/* Login Step */}
        {step === 'login' && (
          <Box component="form" onSubmit={loginForm.handleSubmit(handleLoginSubmit)}>
            <Text c="white" mb="sm">
              Welcome back! Please enter your password.
            </Text>
            <Stack gap="sm">
              <TextInput
                {...loginForm.register('email')}
                size="sm"
                label="Email Address"
                disabled
                styles={textFieldStyles}
              />
              <PasswordInput
                {...loginForm.register('password')}
                size="sm"
                label="Password"
                error={loginForm.formState.errors.password?.message}
                disabled={isLoading}
                styles={textFieldStyles}
              />
            </Stack>
            <Stack pt="lg" pb="sm" gap="sm">
              <Group gap="sm" w="100%" justify="space-between" wrap="nowrap">
                <Button
                  onClick={() => setStep('email')}
                  variant="subtle"
                  c="white"
                  disabled={isLoading}
                  style={{ flex: 1, maxWidth: 120 }}
                >
                  Back
                </Button>
                <Button
                  type="submit"
                  loading={isLoading}
                  style={{ flex: 2 }}
                  styles={{ root: navBarAuthCtaButtonStyles }}
                >
                  Sign In
                </Button>
              </Group>
              <Button
                variant="subtle"
                c="white"
                size="xs"
                onClick={handleForgotPassword}
                style={{ alignSelf: 'center' }}
              >
                Forgot your password?
              </Button>
            </Stack>
          </Box>
        )}
      </Box>
    </Modal>
  );
}
