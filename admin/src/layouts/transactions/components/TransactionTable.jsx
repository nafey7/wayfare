import "./style.css";
import {
  LinearProgress,
  Stack,
  Button,
  Tooltip,
  IconButton,
  Icon,
} from "@mui/material";
import MDDataGrid from "components/MDDataGrid/MDDataGrid";
import MDTypography from "components/MDTypography";
import { centsToDollars } from "global/functions";
import MDBadge from "components/MDBadge";
import { useMaterialUIController } from "context";
import MDBox from "components/MDBox";
import EmptyTableRowOverlay from "components/MDEmptyOverlay/EmptyTableRowOverlay";
import { useEffect, useMemo, useState } from "react";
import CircularIndeterminate from "components/MDLoading";
import MDSnackbar from "components/MDSnackbar";
import { mobileNumberMasking } from "global/functions";
import { debounce, get, isEmpty } from "lodash";
import { capitalizeFirstLetter } from "global/functions";
import { useDispatch, useSelector } from "react-redux";
import { getTransactions } from "store/slice/transactions/transactionSlice";
import moment from "moment";

const TransactionsTable = (props) => {
  const dispatch = useDispatch();
  useState(false);
  const { startDate, endDate, searchText, activeTab } = props;
  const transactionsList = useSelector((state) => state.transactions?.list);
  const totalTransactions = useSelector(
    (state) => state.transactions?.totalTransactions
  );
  const loading = useSelector((state) => state.transactions?.loading);
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(0);
  const [notification, setNotification] = useState({
    color: "",
    icon: "",
    title: "",
    content: "",
    show: false,
    close: () => setNotification({ ...notification, show: false }),
  });
  const [filterModel, setFilterModel] = useState({
    items:
      JSON.parse(localStorage.getItem("transactionalDataGridFilters")) || [],
  });
  const [columnVisibilityModel, setColumnVisibilityModel] = useState(
    JSON.parse(localStorage.getItem("transactionalDataGridColumnVisibility")) ||
      {}
  );
  const [columnOrder, setColumnOrder] = useState(
    JSON.parse(localStorage.getItem("transactionalDataGridColumnOrder")) || []
  );

  const handleFilterChange = (newFilterModel) => {
    setFilterModel(newFilterModel);
    localStorage.setItem(
      "transactionalDataGridFilters",
      JSON.stringify(newFilterModel.items)
    );
  };

  const handleColumnVisibilityChange = (newColumnVisibilityModel) => {
    setColumnVisibilityModel(newColumnVisibilityModel);
    localStorage.setItem(
      "transactionalDataGridColumnVisibility",
      JSON.stringify(newColumnVisibilityModel)
    );
  };

  const handleColumnOrderChange = (newColumnOrder) => {
    setColumnOrder(newColumnOrder);
    localStorage.setItem(
      "transactionalDataGridColumnOrder",
      JSON.stringify(newColumnOrder)
    );
  };

  useEffect(() => {
    const savedFilters = JSON.parse(
      localStorage.getItem("transactionalDataGridFilters")
    );
    if (savedFilters) {
      setFilterModel({ items: savedFilters });
    }
    const savedVisibility = JSON.parse(
      localStorage.getItem("transactionalDataGridColumnVisibility")
    );
    if (savedVisibility) {
      setColumnVisibilityModel(savedVisibility);
    }
    const savedOrder = JSON.parse(
      localStorage.getItem("transactionalDataGridColumnOrder")
    );
    if (savedOrder) {
      setColumnOrder(savedOrder);
    }
  }, []);

  const columnsData = [
    {
      field: "ID",
      headerName: "ID",
      width: 120,
      editable: false,
      renderCell: ({ row }) => {
        let color;
        switch (row.paymentStatus) {
          case "failed":
            color = "red";
            break;
          case "refunded":
            color = "#1b6be4";
            break;
        }

        return (
          <MDTypography display="block" variant="caption" style={{ color }}>
            {row.subscriptionNumber || "-"}
          </MDTypography>
        );
      },
    },

    {
      field: "transactionDate",
      headerName: "Transaction Date",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {` ${moment(row.transactionDate).format("MM DD YYYY hh:mm A")}`}
        </MDTypography>
      ),
    },
    {
      field: "transactionId",
      headerName: "Transaction ID",
      width: 250,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {`${
            row.paymentStatus === "refunded"
              ? get(row, "refundId", get(row, "transactionId", "-"))
              : get(
                  row,
                  "paymentInfo.transactionResponse.transId",
                  get(row, "transactionId", "-")
                )
          }`}
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
          {` ${row.userId?.firstName || "-"} ${row.userId?.lastName || "-"}`}
        </MDTypography>
      ),
    },

    {
      field: "paymentMethodType",
      headerName: "Payment Method",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {row.paymentMethodType === "card"
            ? "Credit card"
            : row.paymentMethodType}
        </MDTypography>
      ),
    },

    {
      field: "paymentGatewayFeePayBy",
      headerName: "Payment Gateway Fee Pay By",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {capitalizeFirstLetter(row.paymentGatewayFeePayBy) || "-"}
        </MDTypography>
      ),
    },

    {
      field: "baseRate",
      headerName: "Base Rate",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {`$${centsToDollars(row?.baseRate)}`}
        </MDTypography>
      ),
    },

    {
      field: "tax",
      headerName: "Tax",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {`$${centsToDollars(row?.tax)}`}
        </MDTypography>
      ),
    },

    {
      field: "serviceFee",
      headerName: "Service Fee",
      width: 100,
      editable: false,
      renderCell: ({ row }) => (
        <>
          <MDTypography
            display="block"
            variant="caption"
            sx={{ color: "black.light" }}
          >
            {row.isApplyServiceFee ? `$${centsToDollars(row.serviceFee)}` : 0}
          </MDTypography>
        </>
      ),
    },
    {
      field: "paymentGatewayFee",
      headerName: "Payment Gateway Fee",
      width: 150,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {`$${centsToDollars(row?.paymentGatewayFee)}`}
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
          {`$${centsToDollars(row?.totalAmount)}`}
        </MDTypography>
      ),
    },
    {
      field: "ownerPayout",
      headerName: "Owner Payout",
      width: 100,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {`$${centsToDollars(row?.ownerPayout)}`}
        </MDTypography>
      ),
    },

    {
      field: "status",
      headerName: "Status",
      width: 120,
      editable: false,
      renderCell: ({ row }) => (
        <MDTypography
          display="block"
          variant="caption"
          sx={{ color: "black.light" }}
        >
          {capitalizeFirstLetter(row?.paymentStatus)}
        </MDTypography>
      ),
    },

    {
      field: "reason",
      headerName: "Failed Reason",
      width: 220,
      editable: false,
      renderCell: ({ row }) => {
        if (row.paymentStatus === "failed") {
          return (
            <MDTypography
              display="block"
              variant="caption"
              sx={{ color: "black.light" }}
            >
              {get(
                row,
                "paymentInfo.transactionResponse.errors[0].errorText",
                get(row, "paymentInfo.message", "-")
              )}
            </MDTypography>
          );
        }
        return (
          <MDTypography
            display="block"
            variant="caption"
            sx={{ color: "black.light" }}
          >
            -
          </MDTypography>
        );
      },
    },
    {
      field: "actions",
      headerName: "Actions",
      width: 200,
      renderCell: ({ row }) => (
        <>
          <Stack direction="row" alignItems="center">
            {row.paymentStatus !== "failed" && (
              <Tooltip title="Download Receipt" placement="top">
                <IconButton
                  color="success"
                  // onClick={() => {
                  //   if (row?.receiptURL) {
                  //     window.open(row?.receiptURL, "_blank");
                  //   }
                  // }}
                >
                  <Icon fontSize="small">download </Icon>
                </IconButton>
              </Tooltip>
            )}
          </Stack>
        </>
      ),
    },
  ];

  const getColumnsByTransactionType = (transactionType) => {
    if (transactionType === "refunded") {
      return columnsData.filter((column) =>
        [
          "transactionId",
          "transactionDate",
          "purpose",
          "subscriptionNumber",
          "licensePlate",
          "totalAmount",
        ].includes(column.field)
      );
    }
    return columnsData;
  };

  const getTransactionsData = async (pageNo) => {
    const payload = {
      pageNo: pageNo || 0,
      status: activeTab === "pendingPayment" ? "initialize" : activeTab,
      search: searchText,
      startDate,
      endDate,
    };
    dispatch(getTransactions(payload));
  };

  const debounceFn = useMemo(
    () => debounce(getTransactionsData, 1000),
    [getTransactionsData]
  );

  useEffect(() => {
    debounceFn();
  }, [startDate, endDate, searchText]);

  const handlePageChange = (params) => {
    getTransactionsData(params.page);
    setPage(params.page);
  };

  const handlePageSizeChange = (params) => {
    setPageSize(params.pageSize);
  };

  return (
    <>
      <MDBox mt={2}>
        <MDDataGrid
          rows={!isEmpty(transactionsList) ? transactionsList : []}
          rowCount={totalTransactions}
          columns={getColumnsByTransactionType(activeTab)}
          getRowId={(row) => row._id}
          disableSelectionOnClick
          loading={loading}
          pagination
          paginationMode="server"
          paginationModel={{ page: page, pageSize: pageSize }}
          onPaginationModelChange={(params) => {
            handlePageChange(params);
          }}
          // getRowClassName={(params) => getRowClassName(params)}
          onPageSizeChange={(params) => handlePageSizeChange(params)}
          components={{
            NoRowsOverlay: EmptyTableRowOverlay,
            LoadingOverlay: LinearProgress,
          }}
          componentsProps={{
            toolbar: {
              showQuickFilter: true,
              quickFilterProps: { debounceMs: 1000 },
            },
          }}
          autoHeight
          filterModel={filterModel}
          onFilterModelChange={handleFilterChange}
          columnVisibilityModel={columnVisibilityModel}
          onColumnVisibilityModelChange={handleColumnVisibilityChange}
          columnOrder={columnOrder}
          onColumnOrderChange={handleColumnOrderChange}
        />
      </MDBox>

      <CircularIndeterminate
        type="full"
        size={20}
        text="Please wait..."
        open={loading}
      />
      <MDSnackbar
        color={notification.color}
        icon={notification.icon}
        title={notification.title}
        content={notification.content}
        open={notification.show}
        close={notification.close}
        bgWhite
      />
    </>
  );
};

export default TransactionsTable;
