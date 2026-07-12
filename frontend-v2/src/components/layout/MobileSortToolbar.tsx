import { type ReactNode, type CSSProperties } from 'react';
import { ActionIcon, Button, Group, Menu, Tooltip } from '@mantine/core';
import { Filter, ArrowUpDown } from 'lucide-react';
import { zIndex } from '@/theme/zIndex';

// Pill-style outlined button: rounded ends, subtle border, on-hover gain
// brand color. Mantine `Button variant="outline"` defaults to a 4 px border
// radius; the explicit `borderRadius: 100` matches the MUI version's pill
// shape (`borderRadius: '100px'`).
const pillButtonStyle: CSSProperties = {
  borderRadius: 100,
  textTransform: 'none',
};

type PrimaryButtonConfig = {
  label: string;
  onClick: () => void;
  startIcon?: ReactNode;
};

type SecondaryActionConfig = {
  label: string;
  icon: ReactNode;
  onClick: () => void;
};

type BaseToolbarProps = {
  primaryButton: PrimaryButtonConfig;
  sortButtonLabel?: string;
  sortStartIcon?: ReactNode;
  /**
   * Optional icon-only action rendered between the Sort menu and the primary
   * (Filters) button — not at the leading edge of the toolbar (the outer
   * Group uses `justify="flex-end"`, so the order in DOM is Sort → secondary
   * → primary).
   */
  secondaryAction?: SecondaryActionConfig;
  /** Merged onto the outer flex container as inline style. */
  style?: CSSProperties;
};

export type MobileSortToolbarValueProps<T extends string> = BaseToolbarProps & {
  sortVariant: 'value';
  menuItems: { value: T; label: string }[];
  selectedSort: T;
  onSortChange: (value: T) => void;
};

export type MobileSortToolbarCustomProps = BaseToolbarProps & {
  sortVariant: 'custom';
  /** Stable key and selection identity (parallel to `value` on the `value` variant). */
  menuItems: { value: string; label: string; selected: boolean; onClick: () => void }[];
};

export type MobileSortToolbarProps<T extends string = string> =
  | MobileSortToolbarValueProps<T>
  | MobileSortToolbarCustomProps;

export function MobileSortToolbar<T extends string>(props: MobileSortToolbarProps<T>) {
  const {
    primaryButton,
    sortButtonLabel = 'Sort',
    sortStartIcon = <ArrowUpDown size={18} />,
    secondaryAction,
    style,
  } = props;

  const primaryStartIcon = primaryButton.startIcon ?? <Filter size={18} />;

  return (
    <Group gap="xs" wrap="wrap" justify="flex-end" style={{ flexShrink: 0, ...style }}>
      {/* zIndex must clear the mobile bottom-sheet (1050) so the dropdown isn't
          occluded when the toolbar is rendered inside a sheet header. */}
      <Menu position="bottom-end" withinPortal zIndex={zIndex.chatSheet}>
        <Menu.Target>
          <Button variant="outline" size="xs" leftSection={sortStartIcon} style={pillButtonStyle}>
            {sortButtonLabel}
          </Button>
        </Menu.Target>
        <Menu.Dropdown>
          {props.sortVariant === 'value'
            ? props.menuItems.map((opt) => {
                const selected = props.selectedSort === opt.value;
                return (
                  <Menu.Item
                    key={opt.value}
                    data-selected={selected || undefined}
                    bg={selected ? 'var(--mantine-color-default-hover)' : undefined}
                    onClick={() => props.onSortChange(opt.value)}
                  >
                    {opt.label}
                  </Menu.Item>
                );
              })
            : props.menuItems.map((opt) => (
                <Menu.Item
                  key={opt.value}
                  data-selected={opt.selected || undefined}
                  bg={opt.selected ? 'var(--mantine-color-default-hover)' : undefined}
                  onClick={opt.onClick}
                >
                  {opt.label}
                </Menu.Item>
              ))}
        </Menu.Dropdown>
      </Menu>
      {secondaryAction ? (
        <Tooltip label={secondaryAction.label} withArrow>
          <ActionIcon
            variant="outline"
            size="lg"
            radius="xl"
            aria-label={secondaryAction.label}
            onClick={secondaryAction.onClick}
          >
            {secondaryAction.icon}
          </ActionIcon>
        </Tooltip>
      ) : null}
      <Button
        variant="outline"
        size="xs"
        leftSection={primaryStartIcon}
        onClick={primaryButton.onClick}
        style={pillButtonStyle}
      >
        {primaryButton.label}
      </Button>
    </Group>
  );
}
