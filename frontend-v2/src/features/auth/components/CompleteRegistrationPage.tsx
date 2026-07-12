import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link as RouterLink } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Alert,
  Anchor,
  Box,
  Button,
  Container,
  Loader,
  Paper,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { palette } from '@/theme/tokens';
import {
  useCompleteRegistrationMutation,
  useValidateRegistrationTokenMutation,
  useGetFrontendConfigQuery,
} from '@/api';
import { useAppDispatch } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { trackEvent } from '@/utils/gtm';
import { getRedirectToChatAfterAuth } from '@/features/auth/utils/authRedirectUtils';
import { ROUTES } from '@/features/routing';
import {
  clearPublicChatPendingCompleteRegistration,
  hasCompleteRegistrationPublicChatHandoffSignals,
} from '@/features/chat/utils/publicChatSignupIntent';
import {
  consumePublicChatReturnTo,
  peekPublicChatReturnTo,
} from '@/features/chat/utils/publicChatReturnRoute';
import { devLog } from '@/utils/devLog';

const completeRegistrationSchema = z
  .object({
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
      .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
      .regex(/[0-9]/, 'Password must contain at least one number'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

type CompleteRegistrationFormData = z.infer<typeof completeRegistrationSchema>;

/**
 * Complete registration page - new user sets password from email link
 */
export function CompleteRegistrationPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [validateToken, { isLoading: isValidating }] =
    useValidateRegistrationTokenMutation();
  const [completeRegistration, { isLoading: isCompleting }] = useCompleteRegistrationMutation();
  const { data: frontendConfig, refetch: refetchFrontendConfig } = useGetFrontendConfigQuery();

  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CompleteRegistrationFormData>({
    resolver: zodResolver(completeRegistrationSchema),
  });

  // Validate token on mount
  useEffect(() => {
    if (!token) {
      setTokenValid(false);
      return;
    }

    validateToken({ token })
      .unwrap()
      .then(() => setTokenValid(true))
      .catch(() => setTokenValid(false));
  }, [token, validateToken]);

  const onSubmit = async (data: CompleteRegistrationFormData) => {
    if (!token) return;

    setError(null);
    try {
      const result = await completeRegistration({
        token,
        password: data.password,
        confirm_password: data.confirmPassword,
      }).unwrap();
      const redirectResult = getRedirectToChatAfterAuth();

      let cfg = frontendConfig;
      if (cfg === undefined) {
        const refetchResult = await refetchFrontendConfig();
        cfg = refetchResult.data ?? undefined;
      }
      const publicChatEnabled = cfg?.publicChatEnabled === true;
      const shouldHandoffToChat =
        publicChatEnabled && hasCompleteRegistrationPublicChatHandoffSignals();

      // Peek before dispatch: the auth update is often committed *after* this handler finishes,
      // so consuming first left localStorage empty while PublicRoute still saw /complete-registration
      // and rendered <Navigate to=/chat>, racing navigate(returnTo).
      const stashedReturnPath = peekPublicChatReturnTo();

      dispatch(setCredentials(result));
      trackEvent('user_registration_completed', { method: 'email', email: result.user.email });

      // Stashed return-to (Tab A) is independent of handoff flags: use it whenever present so
      // email verification tab lands on the correct content page.
      devLog('CompleteRegistration post-auth', {
        stashedReturnPath,
        publicChatEnabled,
        shouldHandoffToChat,
        handoffSignals: hasCompleteRegistrationPublicChatHandoffSignals(),
      });
      if (stashedReturnPath) {
        consumePublicChatReturnTo();
        navigate(stashedReturnPath, { replace: true });
        clearPublicChatPendingCompleteRegistration();
        return;
      }

      if (shouldHandoffToChat) {
        navigate(ROUTES.CHAT);
        clearPublicChatPendingCompleteRegistration();
        return;
      }
      clearPublicChatPendingCompleteRegistration();
      if (redirectResult.redirect === 'chat') {
        navigate(`${ROUTES.CHAT}?prompt=${encodeURIComponent(redirectResult.prompt)}`);
        return;
      }
      navigate(ROUTES.HOME);
    } catch {
      setError('Failed to complete registration. The link may have expired.');
    }
  };

  const isLoading = isValidating || isCompleting;

  return (
    <Box
      style={{
        minHeight: '100vh',
        background: palette.background.gradient,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        paddingBlock: 32,
      }}
    >
      <Container size="sm">
        <Paper p="xl">
          <Title order={1} fw={400} fz="2.125rem" ta="center" mb="md">
            Complete Registration
          </Title>

          {/* Loading state */}
          {isValidating && (
            <Stack align="center" py="lg">
              <Loader />
              <Text c="dimmed" mt="sm">
                Validating your link...
              </Text>
            </Stack>
          )}

          {/* Invalid token */}
          {tokenValid === false && !isValidating && (
            <Stack gap="md">
              <Alert color="red">This registration link is invalid or has expired.</Alert>
              <Text c="dimmed" ta="center">
                Please try registering again to receive a new link.
              </Text>
              <Button fullWidth size="lg" onClick={() => navigate('/login')}>
                Back to Login
              </Button>
            </Stack>
          )}

          {/* Registration form */}
          {tokenValid === true && (
            <>
              <Text c="dimmed" ta="center" mb="md">
                Set a password to complete your account setup.
              </Text>

              {error && (
                <Alert color="red" mb="sm">
                  {error}
                </Alert>
              )}

              <Box component="form" onSubmit={handleSubmit(onSubmit)}>
                <Stack gap="sm">
                  <PasswordInput
                    {...register('password')}
                    label="Password"
                    error={errors.password?.message}
                    disabled={isLoading}
                    autoFocus
                  />
                  <PasswordInput
                    {...register('confirmPassword')}
                    label="Confirm Password"
                    error={errors.confirmPassword?.message}
                    disabled={isLoading}
                  />
                  <Button type="submit" fullWidth size="lg" loading={isCompleting} mt="sm">
                    Complete Registration
                  </Button>
                </Stack>
              </Box>

              <Box style={{ textAlign: 'center', marginTop: 24 }}>
                <Anchor component={RouterLink} to="/login" size="sm">
                  Back to Login
                </Anchor>
              </Box>
            </>
          )}
        </Paper>
      </Container>
    </Box>
  );
}
