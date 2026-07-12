# Voya Admin Dashboard

**Context**: You are working on the admin dashboard. See root `CLAUDE.md` for project-wide information.

## Navigation
📍 **You are here**: Admin Dashboard (`admin/`)
🔙 **Parent**: [Root CLAUDE.md](../CLAUDE.md) - Project overview and role-based quick starts
📚 **Related docs**:
- [FRONTEND_BACKEND_COLLABORATION.md](../docs/FRONTEND_BACKEND_COLLABORATION.md) - API integration patterns
- [ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design

**API Documentation**:
- Swagger UI: http://localhost:8000/api/docs
- Admin endpoints: `/api/admin/*`

## Quick Start
```bash
cd admin
npm install
npm start
```

Access at: http://localhost:3002

## Tech Stack
- **React** 18.2 - UI library
- **Material-UI** - Component library
- **Axios** - HTTP client
- **React Router** v6 - Navigation

## Project Structure
```
src/
├── components/       # Reusable UI components
├── pages/            # Admin pages
│   ├── Dashboard.js  # Overview and metrics
│   ├── Users.js      # User management
│   ├── Bookings.js   # Booking management
│   └── Settings.js   # System settings
├── api/              # Backend API integration
└── App.js            # Root component with routing
```

## Admin Features

### User Management
- View all users with pagination
- Search and filter users
- View user details and activity
- Manage user roles and permissions
- Disable/enable user accounts

### Booking Management
- View all bookings with status
- Search bookings by reference, user, or date
- View booking details
- Manage booking status (pending, confirmed, cancelled)
- Export booking data

### System Settings
- Configure platform settings
- Manage email templates
- View system logs
- Monitor API health and performance

### Analytics Dashboard
- User registration metrics
- Booking statistics
- Revenue tracking
- System performance metrics

## API Integration

### Admin Authentication
```javascript
// Admin-specific endpoints require elevated permissions
const response = await api.get('/api/admin/users', {
  headers: {
    Authorization: `Bearer ${adminToken}`,
  },
});
```

### Admin Endpoints
- `GET /api/admin/users` - List all users
- `GET /api/admin/users/{id}` - Get user details
- `PUT /api/admin/users/{id}` - Update user
- `GET /api/admin/bookings` - List all bookings
- `GET /api/admin/bookings/{id}` - Get booking details
- `GET /api/admin/stats` - Get system statistics

See Swagger UI for complete API documentation: http://localhost:8000/api/docs

## Common Patterns

### Data Tables with Pagination
```jsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TablePagination,
} from '@mui/material';

function UserTable() {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [users, setUsers] = useState([]);

  useEffect(() => {
    async function fetchUsers() {
      const response = await api.get(`/api/admin/users?page=${page}&limit=${rowsPerPage}`);
      setUsers(response.data);
    }
    fetchUsers();
  }, [page, rowsPerPage]);

  return (
    <>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Role</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {users.map(user => (
            <TableRow key={user.id}>
              <TableCell>{user.name}</TableCell>
              <TableCell>{user.email}</TableCell>
              <TableCell>{user.role}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <TablePagination
        component="div"
        count={users.length}
        page={page}
        onPageChange={(e, newPage) => setPage(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(e) => setRowsPerPage(parseInt(e.target.value, 10))}
      />
    </>
  );
}
```

### Search and Filter
```jsx
function UserSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const [users, setUsers] = useState([]);

  const handleSearch = async () => {
    const response = await api.get(`/api/admin/users?search=${searchTerm}`);
    setUsers(response.data);
  };

  return (
    <>
      <TextField
        label="Search users"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
      />
      <Button onClick={handleSearch}>Search</Button>
    </>
  );
}
```

## Development Commands

### Development Server
```bash
npm start              # Start dev server
```

### Code Quality
```bash
npm run lint           # Run ESLint
npm run lint -- --fix  # Auto-fix issues
```

### Build
```bash
npm run build          # Production build
```

## Security Considerations

### Admin Authentication
- Admin users have elevated permissions
- Require strong authentication (MFA recommended)
- Log all admin actions for audit trail

### Data Access
- Only display data admin users are authorized to see
- Implement row-level security in backend
- Never expose sensitive data (passwords, payment info)

### Audit Logging
```javascript
// Log admin actions
async function updateUser(userId, updates) {
  const response = await api.put(`/api/admin/users/${userId}`, updates);

  // Log action
  await api.post('/api/admin/audit-log', {
    action: 'UPDATE_USER',
    user_id: userId,
    changes: updates,
    admin_id: currentAdminId,
  });

  return response.data;
}
```

## Documentation

### Pre-commit Hooks
See root `CLAUDE.md` for pre-commit hook configuration (project-wide).

### Backend Integration
See `docs/FRONTEND_BACKEND_COLLABORATION.md` for API integration patterns.

### Architecture
See `docs/ARCHITECTURE.md` for system design overview.

---

**Last Updated**: October 2025
**Questions**: Create GitHub issue with label `admin`
