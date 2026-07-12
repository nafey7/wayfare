import { LinearProgress } from "@mui/material";
import MDDataGrid from "components/MDDataGrid/MDDataGrid";
import { useState } from "react";
import EmptyTableRowOverlay from "components/MDEmptyOverlay/EmptyTableRowOverlay";
import MDTypography from "components/MDTypography";
import { useSelector } from "react-redux";
import moment from "moment";
import { centsToDollars } from "global/functions";

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
      field: "type",
      headerName: "Plan Type",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.type || "-"}
        </MDTypography>
      ),
    },
    {
      field: "subType",
      headerName: "Plan Sub-Type",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.subType || "-"}`}
        </MDTypography>
      ),
    },
    {
      field: "price",
      headerName: "Price",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` $${centsToDollars(row.price)}`}
        </MDTypography>
      ),
    },
    {
      field: "noOfSearches",
      headerName: "Number of Searches",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.noOfSearches||0}
        </MDTypography>
      ),
    },
    {
      field: "createdAt",
      headerName: "Plan Create On",
      width: 200,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {moment(row.createdAt).format("MM-DD-YYYY hh:mm A")}
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
