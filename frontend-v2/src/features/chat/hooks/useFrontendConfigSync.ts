import { useEffect } from 'react';

import { useGetFrontendConfigQuery } from '@/api';
import type { AppDispatch } from '@/store';
import { markChatConfigHydrated, setConfig } from '@/store/slices/chatSlice';

/**
 * Loads `/config` via RTK Query and mirrors feature flags into the chat slice.
 */
export function useFrontendConfigSync(dispatch: AppDispatch): void {
  const {
    data: frontendConfig,
    isLoading: isFrontendConfigLoading,
    isError: isFrontendConfigError,
  } = useGetFrontendConfigQuery();

  useEffect(() => {
    if (frontendConfig) {
      dispatch(setConfig(frontendConfig));
    }
  }, [frontendConfig, dispatch]);

  useEffect(() => {
    if (!isFrontendConfigLoading && isFrontendConfigError) {
      dispatch(markChatConfigHydrated());
    }
  }, [isFrontendConfigLoading, isFrontendConfigError, dispatch]);
}
