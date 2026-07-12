import { useState, useEffect } from 'react';
import { ActionIcon, Box, Modal, Text } from '@mantine/core';
import { ChevronLeft, ChevronRight, X } from 'lucide-react';

export interface ImageLightboxModalProps {
  open: boolean;
  onClose: () => void;
  /** Image URLs (resolved, ready for img src) */
  images: string[];
  /** Index to show when the modal opens (e.g. match in-card carousel). */
  initialIndex?: number;
  /** Alt text for the displayed image */
  alt?: string;
  fallbackSrc?: string;
}

const navButtonStyle: React.CSSProperties = {
  position: 'absolute',
  top: '50%',
  transform: 'translateY(-50%)',
  zIndex: 2,
};

/**
 * Modal for viewing hotel/room images in enlarged view.
 * When multiple images are provided, shows prev/next arrows to swiper between them.
 */
export function ImageLightboxModal({
  open,
  onClose,
  images,
  initialIndex = 0,
  alt = 'Image',
  fallbackSrc,
}: ImageLightboxModalProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [imageError, setImageError] = useState(false);

  const validImages = images.filter((u) => u && u.trim() !== '');
  const hasMultiple = validImages.length > 1;

  // When the modal opens, sync to `initialIndex` (card carousel position); reset error state.
  useEffect(() => {
    if (!open) return;
    const valid = images.filter((u) => u && u.trim() !== '');
    const maxIdx = Math.max(0, valid.length - 1);
    const start = Math.min(Math.max(initialIndex, 0), maxIdx);
    setCurrentIndex(start);
    setImageError(false);
  }, [open, images, initialIndex]);

  const currentImage = validImages[currentIndex] ?? null;
  const displaySrc = currentImage && !imageError ? currentImage : fallbackSrc;

  const goPrev = () => {
    setCurrentIndex((i) => (i <= 0 ? validImages.length - 1 : i - 1));
    setImageError(false);
  };

  const goNext = () => {
    setCurrentIndex((i) => (i >= validImages.length - 1 ? 0 : i + 1));
    setImageError(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return;
    if (hasMultiple && e.key === 'ArrowLeft') {
      goPrev();
    } else if (hasMultiple && e.key === 'ArrowRight') {
      goNext();
    }
  };

  return (
    <Modal
      opened={open}
      onClose={onClose}
      withCloseButton={false}
      size="auto"
      centered
      padding={0}
      styles={{
        content: {
          maxWidth: '90vw',
          maxHeight: '90vh',
          backgroundColor: 'rgba(0,0,0,0.95)',
        },
      }}
      onKeyDown={handleKeyDown}
      aria-label={`View image ${currentIndex + 1} of ${validImages.length}`}
    >
      <Box
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minWidth: 320,
          minHeight: 240,
          position: 'relative',
        }}
      >
        {/* Close button */}
        <ActionIcon
          onClick={onClose}
          variant="subtle"
          color="gray"
          size="lg"
          style={{ position: 'absolute', top: 8, right: 8, zIndex: 2 }}
          aria-label="Close"
        >
          <X size={24} />
        </ActionIcon>

        {/* Previous arrow */}
        {hasMultiple && (
          <ActionIcon
            onClick={goPrev}
            variant="subtle"
            color="gray"
            size="xl"
            style={{ ...navButtonStyle, left: 8 }}
            aria-label="Previous image"
          >
            <ChevronLeft size={48} />
          </ActionIcon>
        )}

        {/* Image */}
        <Box
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            maxWidth: '100%',
            maxHeight: '90vh',
          }}
        >
          {displaySrc ? (
            <img
              src={displaySrc}
              alt={alt}
              onError={() => setImageError(true)}
              style={{
                maxWidth: '100%',
                maxHeight: '85vh',
                objectFit: 'contain',
              }}
            />
          ) : (
            <Text c="gray.7" size="sm">
              No image available
            </Text>
          )}
        </Box>

        {/* Next arrow */}
        {hasMultiple && (
          <ActionIcon
            onClick={goNext}
            variant="subtle"
            color="gray"
            size="xl"
            style={{ ...navButtonStyle, right: 8 }}
            aria-label="Next image"
          >
            <ChevronRight size={48} />
          </ActionIcon>
        )}

        {/* Image counter */}
        {hasMultiple && (
          <Text
            size="sm"
            c="gray.7"
            style={{
              position: 'absolute',
              bottom: 16,
              left: '50%',
              transform: 'translateX(-50%)',
            }}
          >
            {currentIndex + 1} / {validImages.length}
          </Text>
        )}
      </Box>
    </Modal>
  );
}
