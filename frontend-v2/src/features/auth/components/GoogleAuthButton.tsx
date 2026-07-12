import { useCallback, useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Loader } from '@mantine/core';
import {
  GoogleOAuthProvider,
  GoogleLogin,
  type CredentialResponse,
} from '@react-oauth/google';
import { useGoogleAuthMutation, useGetGoogleConfigQuery } from '@/api';
import { useAppDispatch, useAppSelector } from '@/store';
import { setCredentials } from '@/store/slices/authSlice';
import { selectChatConfig, selectConfigLoaded } from '@/store/slices/chatSlice';
import { clearPublicChatReturnTo } from '@/features/chat/utils/publicChatReturnRoute';
import { shouldPostAuthPreferChatOverHome } from '@/features/chat/utils/publicChatSession';
import { showErrorToast, showErrorToastFromError } from '@/utils/toast';
import { trackEvent } from '@/utils/gtm';
import {
  getRedirectToChatAfterAuth,
  type RedirectCheckResult,
} from '@/features/auth/utils/authRedirectUtils';

interface GoogleAuthButtonProps {
  disabled?: boolean;
  onSuccess?: (redirectResult?: RedirectCheckResult) => void;
}

/**
 * Internal button component that uses GoogleLogin (ID token / credential flow).
 * Must match backend: POST /auth/google/authenticate expects id_token (Google ID token JWT).
 */
function GoogleAuthButtonInner({ disabled, onSuccess }: GoogleAuthButtonProps) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const configLoaded = useAppSelector(selectConfigLoaded);
  const publicChatEnabled = useAppSelector(selectChatConfig).publicChatEnabled;
  const [googleAuth, { isLoading }] = useGoogleAuthMutation();
  const [isLoadingLocal, setLoadingLocal] = useState(false);
  const loading = isLoading || isLoadingLocal;

  const handleSuccess = useCallback(
    async (credentialResponse: CredentialResponse) => {
      const idToken = credentialResponse.credential;
      if (!idToken) {
        showErrorToast('Google Sign-In failed. No credential received.');
        return;
      }
      setLoadingLocal(true);
      try {
        // Backend expects Google ID token (JWT), not OAuth access_token
        const result = await googleAuth({ id_token: idToken }).unwrap();
        const redirectResult = getRedirectToChatAfterAuth();
        dispatch(setCredentials(result));
        trackEvent('user_login', { method: 'google', email: result.user.email });
        if (result.isNew) {
          trackEvent('user_registered', { method: 'google', email: result.user.email });
          trackEvent('user_registration_completed', { method: 'google', email: result.user.email });
        }

        if (onSuccess) {
          onSuccess(redirectResult);
        } else {
          clearPublicChatReturnTo();
          if (redirectResult.redirect === 'chat') {
            navigate(`/chat?prompt=${encodeURIComponent(redirectResult.prompt)}`);
            return;
          }
          if (configLoaded && shouldPostAuthPreferChatOverHome(publicChatEnabled)) {
            navigate('/chat');
            return;
          }
          navigate('/home');
        }
      } catch (error) {
        trackEvent('user_login_failed', {
          method: 'google',
          error: error instanceof Error ? error.message : 'Google OAuth failed',
        });
        showErrorToastFromError(error, 'Google sign-in failed. Please try again.');
      } finally {
        setLoadingLocal(false);
      }
    },
    [googleAuth, dispatch, navigate, onSuccess, configLoaded, publicChatEnabled]
  );

  const handleError = useCallback(() => {
    trackEvent('user_login_failed', {
      method: 'google',
      error: 'Google Sign-In failed',
    });
    showErrorToast('Google sign-in failed. Please try again.');
  }, []);

  const containerRef = useRef<HTMLDivElement>(null);
  const [widthPx, setWidthPx] = useState(400);

  useEffect(() => {
    if (!containerRef.current) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (typeof w === 'number' && w > 0) setWidthPx(Math.round(w));
    });
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  const wrapperStyle: React.CSSProperties = {
    width: '100%',
    position: 'relative',
    ...((disabled || loading) && { pointerEvents: 'none', opacity: 0.7 }),
  };

  return (
    <div ref={containerRef} style={wrapperStyle}>
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={handleError}
        useOneTap={false}
        theme="outline"
        size="large"
        text="continue_with"
        shape="pill"
        width={String(widthPx)}
      />
      {loading && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            zIndex: 1,
          }}
        >
          <Loader size="sm" />
        </div>
      )}
    </div>
  );
}

/**
 * Google OAuth button wrapped with provider
 */
export function GoogleAuthButton({ disabled, onSuccess }: GoogleAuthButtonProps) {
  const { data: config, isLoading } = useGetGoogleConfigQuery();

  if (isLoading) {
    return (
      <Button variant="outline" fullWidth size="lg" disabled leftSection={<Loader size="xs" />}>
        Loading…
      </Button>
    );
  }

  if (!config?.enabled || !config?.clientId) {
    // Google auth not configured
    return null;
  }

  return (
    <GoogleOAuthProvider clientId={config.clientId}>
      <GoogleAuthButtonInner disabled={disabled} onSuccess={onSuccess} />
    </GoogleOAuthProvider>
  );
}
