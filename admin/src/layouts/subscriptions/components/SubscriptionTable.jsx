import { LinearProgress, Stack, Checkbox } from "@mui/material";
import MDDataGrid from "components/MDDataGrid/MDDataGrid";
import MDTypography from "components/MDTypography";
import { centsToDollars } from "global/functions";
import MDBox from "components/MDBox";
import EmptyTableRowOverlay from "components/MDEmptyOverlay/EmptyTableRowOverlay";
import { useState } from "react";
import { getSubscriptionDuration } from "global/functions";
import { mobileNumberMasking } from "global/functions";
import { getTimezoneName } from "global/functions";
import MDButton from "components/MDButton";
import Label from "components/Common/Label";
import { isEmpty } from "lodash";

const SubscriptionsTable = (props) => {
  const { subscriptionList, subscriptionType, isLoading } = props;
  const [selectedSubscriptionIds, setSelectedSubscriptionIds] = useState([]);

  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });

  const handleSelectAll = (checked) => {
    if (checked) {
      const allRowIds = subscriptionList.map((row) => row._id);
      setSelectedSubscriptionIds(allRowIds);
    } else {
      setSelectedSubscriptionIds([]);
    }
  };

  const columnsData = [
    {
      field: "subscriptionNumber",
      headerName: "Subscription ID",
      width: 120,
      editable: false,
      renderCell: ({ row }) => {
        let color;
        switch (row.subscriptionStatus) {
          case "failed":
            color = "red";
            break;
          case "refunded":
            color = "#1b6be4";
            break;
          case "cancel":
            color = "#f5b642";
            break;
        }
        return (
          <>
            <MDTypography display="block" variant="caption" style={{ color }}>
              {` ${row.subscriptionNumber || "-"}`}
            </MDTypography>
          </>
        );
      },
    },

    {
      field: "duration",
      headerName: "Duration",
      width: 180,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography display="block" variant="caption">
          {getSubscriptionDuration({
            startDate: row.startDate,
            endDate: row.endDate,
            tz: getTimezoneName(),
          })}
        </MDTypography>
      ),
    },

    {
      field: "email",
      headerName: "Email",
      width: 180,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.userId?.email || "-"}`}
        </MDTypography>
      ),
    },
    {
      field: "cellPhone",
      headerName: "Cell Phone",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${
            row.userId?.isPhoneNumber
              ? mobileNumberMasking(row.userId.mobile)
              : "-"
          }`}
        </MDTypography>
      ),
    },

    {
      field: "name",
      headerName: "Name",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${row.userId?.firstName || ""} ${row.userId?.lastName || ""}`}
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
          {row?.paymentMethodType === "card"
            ? "Credit Card"
            : row.paymentId?.paymentMethodType || "-"}
        </MDTypography>
      ),
    },
    {
      field: "isAutoRenew",
      headerName: "Is Auto Renew",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.isAutoRenew ? "Yes" : "No"}
        </MDTypography>
      ),
    },

    {
      field: "totalAmount",
      headerName: "Total Amount",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <>
          {row.isMonthly &&
          row.renewalCount === 0 &&
          row?.totalAmount !== row?.firstMonthTotalAmount ? (
            <>
              <Stack direction="row" spacing={1}>
                <MDTypography
                  display="block"
                  variant="caption"
                  sx={{ color: "black.light", textDecoration: "line-through" }}
                >
                  {`$${centsToDollars(row?.totalAmount)}`}
                </MDTypography>
                <MDTypography
                  display="block"
                  variant="caption"
                  sx={{ color: "black.light" }}
                >
                  {`$${centsToDollars(row?.firstMonthTotalAmount)}`}
                </MDTypography>
              </Stack>
            </>
          ) : (
            <MDTypography
              display="block"
              variant="caption"
              sx={{ color: "black.light" }}
            >
              {`$${centsToDollars(row?.totalAmount)}`}
            </MDTypography>
          )}
        </>
      ),
    },

    // {
    //   field: "actions",
    //   headerName: "Actions",
    //   width: 120,

    //   renderCell: ({ row }) => <></>,
    // },
  ];

  return (
    <>
      <MDBox mt={selectedSubscriptionIds.length > 0 ? 0 : 2}>
        <MDDataGrid
          rows={!isEmpty(subscriptionList) ? subscriptionList : []}
          columns={columnsData}
          getRowId={(row) => row._id}
          pageSize={10}
          rowsPerPageOptions={[10]}
          disableSelectionOnClick
          loading={isLoading}
          components={{
            NoRowsOverlay: EmptyTableRowOverlay,
            LoadingOverlay: LinearProgress,
          }}
          componentsProps={{
            toolbar: {
              showQuickFilter: true,
              quickFilterProps: { debounceMs: 500 },
            },
          }}
          autoHeight
        />
      </MDBox>
    </>
  );
};

export default SubscriptionsTable;
