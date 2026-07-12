import { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Alert,
  Anchor,
  Box,
  Button,
  Container,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { palette } from '@/theme/tokens';
import { useForgotPasswordMutation } from '@/api';
import { trackEvent } from '@/utils/gtm';

const forgotPasswordSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

/**
 * Forgot password page - request password reset email
 */
export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [forgotPassword, { isLoading }] = useForgotPasswordMutation();
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setError(null);
    try {
      await forgotPassword(data).unwrap();
      trackEvent('user_password_reset_requested');
      setSubmitted(true);
    } catch {
      setError('Failed to send reset email. Please try again.');
    }
  };

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
          {/* Preserve MUI h4 size (~34 px) via explicit fz; tokens.h4 is 1.125 rem
              which is too small for an auth page title. See heading-size note in
              MANTINE_MIGRATION_PATTERN.md. */}
          <Title order={1} fw={400} fz="2.125rem" ta="center" mb="md">
            Reset Password
          </Title>

          {submitted ? (
            <Stack gap="md">
              <Alert color="green">
                If an account exists with this email, you will receive a password reset
                link shortly.
              </Alert>
              <Text c="dimmed" ta="center">
                Please check your email and follow the instructions to reset your password.
              </Text>
              <Button fullWidth size="lg" onClick={() => navigate('/login')}>
                Back to Login
              </Button>
            </Stack>
          ) : (
            <>
              <Text c="dimmed" ta="center" mb="md">
                Enter your email address and we'll send you a link to reset your password.
              </Text>

              {error && (
                <Alert color="red" mb="sm">
                  {error}
                </Alert>
              )}

              <Box component="form" onSubmit={handleSubmit(onSubmit)}>
                <TextInput
                  {...register('email')}
                  label="Email"
                  type="email"
                  error={errors.email?.message}
                  disabled={isLoading}
                  autoFocus
                />
                <Button
                  type="submit"
                  fullWidth
                  size="lg"
                  loading={isLoading}
                  mt="md"
                >
                  Send Reset Link
                </Button>
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
