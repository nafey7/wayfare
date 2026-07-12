import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { within, expect } from 'storybook/test';
import { Button } from '@mantine/core';
import hotelFallback from '@/assets/images/hotels/hotel-fallback.svg';
import { ImageLightboxModal } from './ImageLightboxModal';
import { mockImageUrls, singleImageUrl } from '../__fixtures__/mockHotelDetailData';

const meta: Meta<typeof ImageLightboxModal> = {
  title: 'Hotels/ImageLightboxModal',
  component: ImageLightboxModal,
};

export default meta;
type Story = StoryObj<typeof ImageLightboxModal>;

/**
 * Open-state decorator: mounts the modal in open state and asserts against its content.
 * The Dialog renders into a MUI Portal outside canvasElement — use document.body.
 */

export const Default: Story = {
  name: 'Open — multiple images',
  args: {
    open: true,
    onClose: () => {},
    images: mockImageUrls,
    initialIndex: 0,
    alt: 'Hotel room',
    fallbackSrc: hotelFallback,
  },
  play: async () => {
    // Dialog renders into a Portal — assert against body
    const closeBtn = document.querySelector('[aria-label="Close"]');
    expect(closeBtn, 'expected Close button to be present in open modal').toBeTruthy();
    // Navigation arrows should be present for multiple images
    const prevBtn = document.querySelector('[aria-label="Previous image"]');
    const nextBtn = document.querySelector('[aria-label="Next image"]');
    expect(prevBtn, 'expected Previous image button').toBeTruthy();
    expect(nextBtn, 'expected Next image button').toBeTruthy();
  },
};

export const SingleImage: Story = {
  name: 'Open — single image (no arrows)',
  args: {
    open: true,
    onClose: () => {},
    images: singleImageUrl,
    initialIndex: 0,
    alt: 'Hotel exterior',
    fallbackSrc: hotelFallback,
  },
  play: async () => {
    const closeBtn = document.querySelector('[aria-label="Close"]');
    expect(closeBtn, 'expected Close button').toBeTruthy();
    // No navigation arrows for single image
    const prevBtn = document.querySelector('[aria-label="Previous image"]');
    const nextBtn = document.querySelector('[aria-label="Next image"]');
    expect(prevBtn, 'expected no Previous button for single image').toBeNull();
    expect(nextBtn, 'expected no Next button for single image').toBeNull();
  },
};

export const ManyImages: Story = {
  name: 'Open — many images (5), starts at index 2',
  args: {
    open: true,
    onClose: () => {},
    images: mockImageUrls,
    initialIndex: 2,
    alt: 'Hotel gallery',
    fallbackSrc: hotelFallback,
  },
  play: async () => {
    const closeBtn = document.querySelector('[aria-label="Close"]');
    expect(closeBtn, 'expected Close button').toBeTruthy();
  },
};

export const Closed: Story = {
  name: 'Closed state (null render)',
  args: {
    open: false,
    onClose: () => {},
    images: mockImageUrls,
    alt: 'Hotel room',
    fallbackSrc: hotelFallback,
  },
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Component returns null when closed — no dialog content in canvas
    const dialog = canvas.queryByRole('dialog');
    expect(dialog, 'expected no dialog when closed').toBeNull();
  },
};

/**
 * Interactive story — shows a trigger button that opens the modal.
 * Good for manual visual review.
 */
function InteractiveLightbox() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="contained" onClick={() => setOpen(true)}>
        Open Lightbox
      </Button>
      <ImageLightboxModal
        open={open}
        onClose={() => setOpen(false)}
        images={mockImageUrls}
        alt="Hotel gallery"
        fallbackSrc={hotelFallback}
      />
    </>
  );
}

export const Interactive: Story = {
  name: 'Interactive (click to open)',
  render: () => <InteractiveLightbox />,
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const btn = canvas.getByRole('button', { name: 'Open Lightbox' });
    expect(btn, 'expected Open Lightbox button').toBeTruthy();
  },
};
