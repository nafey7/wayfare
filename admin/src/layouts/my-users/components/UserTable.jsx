import { LinearProgress } from "@mui/material";
import MDDataGrid from "components/MDDataGrid/MDDataGrid";
import { useState } from "react";
import EmptyTableRowOverlay from "components/MDEmptyOverlay/EmptyTableRowOverlay";
import MDTypography from "components/MDTypography";
import { useSelector } from "react-redux";
import moment from "moment";

const UserTable = (props) => {
  const { userData } = props;
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const loading = useSelector((state) => state.users?.loading);
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });

  const columnsData = [
    {
      field: "fullName",
      headerName: "Full Name",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row?.firstName?.concat(" ", row?.lastName)}
        </MDTypography>
      ),
    },
    {
      field: "email",
      headerName: "Email ID",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.email||"-"}`}
        </MDTypography>
      ),
    },
    {
      field: "mobile",
      headerName: "Mobile No",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.mobile||"-"}`}
        </MDTypography>
      ),
    },
    {
      field: "isPlanActive",
      headerName: "Active Plan",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.isPlanActive?"Yes":"No"}
        </MDTypography>
      ),
    },
    {
      field: "lastLoginDate",
      headerName: "Last Login Date",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {moment(row.lastLoginDate).format("MM-DD-YYYY hh:mm A")}
        </MDTypography>
      ),
    },
  ];

  return (
    <>
      <MDDataGrid
        rows={userData ?? []}
        columns={columnsData}
        getRowId={(row) => row?._id}
        pagination
        page={page}
        pageSize={pageSize}
        paginationMode="server"
        onPageChange={(newPage) => setPage(newPage)}
        onPageSizeChange={(newPageSize) => setPageSize(newPageSize)}
        disableSelectionOnClick={true}
        components={{
          NoRowsOverlay: EmptyTableRowOverlay,
          LoadingOverlay: LinearProgress,
        }}
        loading={loading}
      />
    </>
  );
};

export default UserTable;
