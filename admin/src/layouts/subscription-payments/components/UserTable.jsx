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
      field: "customerName",
      headerName: "Customer Name",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.userId?.firstName || "-"} {row.userId?.lastName || "-"}
        </MDTypography>
      ),
    },
    {
      field: "createdAt",
      headerName: "Plan Purchased On",
      width: 150,
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
          {row.planId?.type || "-"}
        </MDTypography>
      ),
    },
    {
      field: "subType",
      headerName: "Plan Sub-Type",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.planId?.subType || "-"}
        </MDTypography>
      ),
    },
    {
      field: "noOfSearches",
      headerName: "Number of Searches",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.planId?.noOfSearches || 0}`}
        </MDTypography>
      ),
    },
    {
      field: "paymentMethodType",
      headerName: "Payment Method",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.paymentId?.paymentMethodType === "card"
            ? "Credit Card"
            : row.paymentId?.paymentMethodType || "-"}
        </MDTypography>
      ),
    },
    {
      field: "basePrice",
      headerName: "Base Price",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` $ ${centsToDollars(row.paymentId?.baseRate)}`}
        </MDTypography>
      ),
    },
    {
      field: "applicationFee",
      headerName: "Platform Fee",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` $ ${centsToDollars(row.paymentId?.applicationFee)}`}
        </MDTypography>
      ),
    },
    {
      field: "totalAmount",
      headerName: "Total Amount",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` $ ${centsToDollars(row.paymentId?.totalAmount)}`}
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
