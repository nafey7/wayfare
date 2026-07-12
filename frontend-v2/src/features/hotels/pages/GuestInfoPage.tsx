/**
 * Legacy route: guest details are collected on the combined review page.
 * Route: /hotels/guest-info → redirects to /hotels/review-booking
 */
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Container, Loader } from '@mantine/core';

export function GuestInfoPage() {
  const navigate = useNavigate();
  useEffect(() => {
    navigate('/hotels/review-booking', { replace: true });
  }, [navigate]);
  return (
    <Container size="md" py="xl">
      <Loader />
    </Container>
  );
}
