import { Outlet } from 'react-router-dom';
import { MainLayout } from './MainLayout';

/**
 * Layout route for authenticated pages that should NOT show the persistent chat panel.
 * Keeps the header consistent by using MainLayout, and renders the page via Outlet.
 */
export function LayoutNoChat() {
  return (
    <MainLayout>
      <Outlet />
    </MainLayout>
  );
}
