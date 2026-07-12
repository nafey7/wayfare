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
import { useValidateResetTokenMutation, useResetPasswordMutation } from '@/api';

const resetPasswordSchema = z
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

type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

/**
 * Reset password page - set new password using token from email
 */
export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  const [validateToken, { isLoading: isValidating }] = useValidateResetTokenMutation();
  const [resetPassword, { isLoading: isResetting }] = useResetPasswordMutation();

  const [tokenValid, setTokenValid] = useState<boolean | null>(null);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
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

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token) return;

    setError(null);
    try {
      await resetPassword({
        token,
        new_password: data.password,
        confirm_password: data.confirmPassword,
      }).unwrap();
      setSuccess(true);
    } catch {
      setError('Failed to reset password. The link may have expired.');
    }
  };

  const isLoading = isValidating || isResetting;

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
            Set New Password
          </Title>

          {/* Loading state */}
          {isValidating && (
            <Stack align="center" py="lg">
              <Loader />
              <Text c="dimmed" mt="sm">
                Validating reset link...
              </Text>
            </Stack>
          )}

          {/* Invalid token */}
          {tokenValid === false && !isValidating && (
            <Stack gap="md">
              <Alert color="red">This password reset link is invalid or has expired.</Alert>
              <Button fullWidth size="lg" onClick={() => navigate('/forgot-password')}>
                Request New Reset Link
              </Button>
            </Stack>
          )}

          {/* Success state */}
          {success && (
            <Stack gap="md">
              <Alert color="green">Your password has been reset successfully.</Alert>
              <Button fullWidth size="lg" onClick={() => navigate('/login')}>
                Sign In
              </Button>
            </Stack>
          )}

          {/* Reset form */}
          {tokenValid === true && !success && (
            <>
              <Text c="dimmed" ta="center" mb="md">
                Enter your new password below.
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
                    label="New Password"
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
                  <Button type="submit" fullWidth size="lg" loading={isResetting} mt="sm">
                    Reset Password
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
