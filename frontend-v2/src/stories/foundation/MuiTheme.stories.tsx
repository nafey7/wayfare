import type { Meta, StoryObj } from '@storybook/react-vite';
import { expect, within } from 'storybook/test';
import {
  Box,
  Button,
  ButtonGroup,
  Stack,
  Typography,
  Chip,
  TextField,
  Card,
  CardContent,
  CardActions,
  Divider,
  Badge,
  Paper,
  useTheme,
} from '@mui/material';
import FlightIcon from '@mui/icons-material/Flight';
import HotelIcon from '@mui/icons-material/Hotel';
import StarIcon from '@mui/icons-material/Star';

function ColorSwatch({ label, hex }: { label: string; hex: string }) {
  return (
    <Stack alignItems="center" spacing={0.5} sx={{ width: 80 }}>
      <Box
        sx={{
          width: 64,
          height: 64,
          borderRadius: 2,
          backgroundColor: hex,
          border: '1px solid rgba(0,0,0,0.07)',
        }}
      />
      <Typography variant="caption" align="center" sx={{ lineHeight: 1.2 }}>{label}</Typography>
      <Typography variant="caption" align="center" color="text.secondary" sx={{ fontFamily: 'monospace' }}>{hex}</Typography>
    </Stack>
  );
}

function MuiThemeShowcase() {
  const theme = useTheme();

  const paletteGroups = [
    {
      title: 'Primary — #BFC6F4 (lavender, MUI production)',
      swatches: [
        { label: 'light', hex: theme.palette.primary.light },
        { label: 'main', hex: theme.palette.primary.main },
        { label: 'dark', hex: theme.palette.primary.dark },
      ],
    },
    {
      title: 'Secondary — #7C83D0',
      swatches: [
        { label: 'light', hex: theme.palette.secondary.light },
        { label: 'main', hex: theme.palette.secondary.main },
        { label: 'dark', hex: theme.palette.secondary.dark },
      ],
    },
    {
      title: 'Success',
      swatches: [
        { label: 'light', hex: theme.palette.success.light },
        { label: 'main', hex: theme.palette.success.main },
        { label: 'dark', hex: theme.palette.success.dark },
      ],
    },
    {
      title: 'Error',
      swatches: [
        { label: 'light', hex: theme.palette.error.light },
        { label: 'main', hex: theme.palette.error.main },
        { label: 'dark', hex: theme.palette.error.dark },
      ],
    },
  ];

  return (
    <Stack spacing={4} p={4} maxWidth={900}>
      <Typography variant="h4" fontWeight={700}>MUI Theme — Voya</Typography>

      {/* Palette groups */}
      {paletteGroups.map(({ title, swatches }) => (
        <Stack key={title} spacing={1}>
          <Typography variant="h6">{title}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {swatches.map((s) => (
              <ColorSwatch key={s.label} label={s.label} hex={s.hex} />
            ))}
          </Stack>
        </Stack>
      ))}

      <Divider />

      {/* Voya-specific colours */}
      <Stack spacing={1}>
        <Typography variant="h6">Chat colours</Typography>
        <Stack direction="row" spacing={1}>
          <ColorSwatch label="botMessage" hex={theme.palette.chat.botMessage} />
          <ColorSwatch label="userMessage" hex={theme.palette.chat.userMessage} />
          <ColorSwatch label="figmaBase" hex={theme.palette.figmaBase} />
        </Stack>
      </Stack>

      <Divider />

      {/* Gradient */}
      <Stack spacing={1}>
        <Typography variant="h6">Gradient (navbar / header)</Typography>
        <Box
          sx={{
            height: 80,
            borderRadius: 3,
            background: theme.palette.background.gradient,
            display: 'flex',
            alignItems: 'center',
            pl: 3,
          }}
        >
          <Typography color="white" fontWeight={600} variant="h6">Voya — Your perfect trip</Typography>
        </Box>
      </Stack>

      <Divider />

      {/* Buttons */}
      <Stack spacing={1}>
        <Typography variant="h6">Buttons</Typography>
        <Typography variant="body2" color="text.secondary">contained · outlined · text</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button variant="contained">Book now</Button>
          <Button variant="contained" color="secondary">View flights</Button>
          <Button variant="outlined">Outline</Button>
          <Button variant="text">Text</Button>
          <Button variant="contained" disabled>Disabled</Button>
          <Button variant="contained" startIcon={<FlightIcon />}>Flights</Button>
          <Button variant="contained" startIcon={<HotelIcon />} color="secondary">Hotels</Button>
        </Stack>
        <ButtonGroup variant="outlined">
          <Button>Economy</Button>
          <Button>Business</Button>
          <Button>First</Button>
        </ButtonGroup>
      </Stack>

      <Divider />

      {/* Typography */}
      <Stack spacing={0.5}>
        <Typography variant="h6" gutterBottom>Typography (Lato)</Typography>
        <Typography variant="h1">h1 — Lato 700</Typography>
        <Typography variant="h2">h2 — Lato</Typography>
        <Typography variant="h3">h3 — Lato</Typography>
        <Typography variant="h4">h4 — Lato</Typography>
        <Typography variant="h5">h5 — Lato</Typography>
        <Typography variant="h6">h6 — Lato</Typography>
        <Typography variant="body1">body1 — regular text</Typography>
        <Typography variant="body2">body2 — secondary text</Typography>
        <Typography variant="caption" display="block" color="text.secondary">caption / dimmed</Typography>
      </Stack>

      <Divider />

      {/* Chips */}
      <Stack spacing={1}>
        <Typography variant="h6">Chips</Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Chip label="Best value" color="primary" icon={<StarIcon />} />
          <Chip label="Direct" color="success" />
          <Chip label="Confirmed" color="secondary" />
          <Chip label="Cancelled" color="error" />
          <Chip label="1 Stop" variant="outlined" color="primary" />
          <Chip label="Bold action" variant="boldAction" />
        </Stack>
      </Stack>

      <Divider />

      {/* Inputs */}
      <Stack spacing={2} maxWidth={400}>
        <Typography variant="h6">Inputs</Typography>
        <TextField label="From" placeholder="City or airport" variant="outlined" />
        <TextField label="To" placeholder="City or airport" variant="outlined" />
        <TextField label="Departure" placeholder="dd / mm / yyyy" variant="outlined" />
      </Stack>

      <Divider />

      {/* Cards */}
      <Stack spacing={1}>
        <Typography variant="h6">Cards</Typography>
        <Stack direction="row" spacing={2} flexWrap="wrap" alignItems="flex-start">
          <Card sx={{ width: 220 }}>
            <CardContent>
              <Stack direction="row" justifyContent="space-between" mb={1}>
                <Chip label="Flight" size="small" color="primary" />
                <Chip label="Direct" size="small" variant="outlined" />
              </Stack>
              <Typography fontWeight={700} variant="h6">LHR → CDG</Typography>
              <Typography variant="body2" color="text.secondary">09:00 → 11:15 · 2h 15m</Typography>
            </CardContent>
            <Divider />
            <CardActions sx={{ justifyContent: 'space-between', px: 2, py: 1 }}>
              <Typography fontWeight={700} variant="h6" color="secondary.dark">£89</Typography>
              <Button variant="contained" size="small">Book</Button>
            </CardActions>
          </Card>

          <Card sx={{ width: 220 }}>
            <CardContent>
              <Chip label="Best value ⭐" size="small" color="success" sx={{ mb: 1 }} />
              <Typography fontWeight={700} variant="h6">The Grand Paris</Typography>
              <Typography variant="body2" color="text.secondary">★ 4.8 · City centre</Typography>
              <Typography variant="caption" color="text.secondary">Free cancellation</Typography>
            </CardContent>
            <Divider />
            <CardActions sx={{ justifyContent: 'space-between', px: 2, py: 1 }}>
              <Typography fontWeight={700} variant="h6" color="secondary.dark">
                £145<Typography component="span" variant="caption" color="text.secondary">/night</Typography>
              </Typography>
              <Button variant="outlined" size="small">Rooms</Button>
            </CardActions>
          </Card>

          <Paper
            elevation={3}
            sx={{
              width: 220,
              p: 2,
              background: theme.palette.background.gradient,
              borderRadius: 3,
            }}
          >
            <Typography color="white" variant="caption" sx={{ opacity: 0.7 }}>YOUR TRIP</Typography>
            <Typography color="white" fontWeight={700} variant="h6">Tokyo · 7 days</Typography>
            <Typography color="white" variant="body2" sx={{ opacity: 0.85 }}>3 flights · 2 hotels</Typography>
            <Button
              variant="contained"
              size="small"
              fullWidth
              sx={{ mt: 1.5, backgroundColor: '#E7FBBC', color: '#1a1a1a', '&:hover': { backgroundColor: '#d4f78e' } }}
            >
              View itinerary
            </Button>
          </Paper>
        </Stack>
      </Stack>

      {/* Badge */}
      <Stack spacing={1}>
        <Typography variant="h6">Badges</Typography>
        <Stack direction="row" spacing={3}>
          <Badge badgeContent={3} color="primary">
            <FlightIcon />
          </Badge>
          <Badge badgeContent={1} color="error">
            <HotelIcon />
          </Badge>
          <Badge variant="dot" color="success">
            <Typography>Live</Typography>
          </Badge>
        </Stack>
      </Stack>

    </Stack>
  );
}

const meta: Meta<typeof MuiThemeShowcase> = {
  title: 'Foundation/MuiTheme',
  component: MuiThemeShowcase,
};

export default meta;
type Story = StoryObj<typeof MuiThemeShowcase>;

export const Default: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    // Primary palette values must render in colour swatches — catches theme regression
    expect(canvas.getAllByText('#BFC6F4').length).toBeGreaterThan(0); // primary.main
    expect(canvas.getAllByText('#7C83D0').length).toBeGreaterThan(0); // secondary.main
  },
};
