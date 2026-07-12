import Card from "@mui/material/Card";
import Grid from "@mui/material/Grid";
import breakpoints from "assets/theme/base/breakpoints";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";
import MDButton from "components/MDButton";
import { useMaterialUIController } from "context";
import { useEffect, useState } from "react";
import Footer from "examples/Footer";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import { useSelector, useDispatch } from "react-redux";
import { useLocation, useNavigate } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import DirectionsCarIcon from "@mui/icons-material/DirectionsCar";
import CancelIcon from "@mui/icons-material/Cancel";
import ExploreOffIcon from "@mui/icons-material/ExploreOff";
import * as XLSX from "xlsx";

import SubscriptionsTable from "./components/SubscriptionTable";
import { isEmpty, sortBy } from "lodash";
import moment from "moment";
import { amountToShow } from "global/functions";
import DownloadIcon from "@mui/icons-material/Download";
import { getSubscriptions } from "store/slice/subscriptions/subscriptionSlice";

function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`full-width-tabpanel-${index}`}
      aria-labelledby={`full-width-tab-${index}`}
      {...other}
    >
      {value === index && <MDBox sx={{ p: 3 }}>{children}</MDBox>}
    </div>
  );
}

function Subscriptions() {
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const userData = useSelector((state) => state.users?.meInfo);
  const roleModules = userData?.roleModules || {};
  const [tabsOrientation, setTabsOrientation] = useState("horizontal");
  const queryParams = new URLSearchParams(location.search);
  const activeTab = queryParams.get("tab");
  const [tabValue, setTabValue] = useState(activeTab ? activeTab : "active");
  const isLoading = useSelector((state) => state.subscriptions.loading);
  const subscriptionsList = useSelector(
    (state) => state.subscriptions?.subscriptions || []
  );

  const currentDate = moment();

  useEffect(() => {
    function handleTabsOrientation() {
      return window.innerWidth < breakpoints.values.sm
        ? setTabsOrientation("vertical")
        : setTabsOrientation("horizontal");
    }

    window.addEventListener("resize", handleTabsOrientation);
    handleTabsOrientation();
    return () => window.removeEventListener("resize", handleTabsOrientation);
  }, [tabsOrientation]);

  const handleSetTabValue = (event, newValue) => {
    setTabValue(newValue);
    queryParams.set("tab", newValue);
    const updatedQueryString = queryParams.toString();
    navigate(`?${updatedQueryString}`);
  };

  useEffect(() => {
    dispatch(getSubscriptions());
  }, [dispatch, activeTab]);

  const downloadReport = (data) => {
    const subscriptionsList = data.filter((item) => {
      const startDate = moment(item.startDate);
      const endDate = moment(item.endDate);
      const isExpired = currentDate.isAfter(endDate);

      switch (tabValue) {
        case "active":
          return (
            ((item.subscriptionStatus === "active" ||
              item.subscriptionStatus === "cancel") &&
              !item.isSubscriptionPaused &&
              currentDate.isBetween(
                startDate,
                endDate.add(1, "days"),
                null,
                "[]"
              )) ||
            (item.subscriptionStatus === "active" &&
              startDate.isAfter(currentDate) &&
              endDate.isAfter(currentDate))
          );
        case "canceled":
          return item.subscriptionStatus === "cancel";
        case "expired":
          return (
            !item.isSubscriptionPaused &&
            isExpired &&
            item.subscriptionStatus !== "pending" &&
            item.subscriptionStatus !== "initialize"
          );
        case "pending":
          return item.subscriptionStatus === "pending";
        case "failed":
          return item.subscriptionStatus === "failed";
        default:
          return false;
      }
    });

    const columnMapping = {
      "Subscription ID": "subscriptionNumber",
      "Start Date": "startDate",
      "End Date": "endDate",
      Email: "userId.email",
      Mobile: "userId.mobile",
      Name: "userId.fullName",
      "Auto Renew": "isAutoRenew",
      "Payment Method": "paymentMethodType",
      "Total Amount": "totalAmount",
    };

    const filteredData = subscriptionsList.map((item) => {
      const filteredItem = {};
      Object.keys(columnMapping).forEach((columnName) => {
        const key = columnMapping[columnName];
        let value = item[key];
        if (key === "userId.fullName") {
          const firstName =
            item.userId && item.userId.firstName
              ? item.userId.firstName
              : "";
          const lastName =
            item.userId && item.userId.lastName
              ? item.userId.lastName
              : "";
          value = `${firstName} ${lastName}`.trim();
        } else if (key === "startDate" || key === "endDate") {
          value = value ? new Date(value).toLocaleDateString("en-US") : "";
        } else if (key === "userId.email") {
          value =
            item["userId"] && item["userId"]["email"]
              ? item["userId"]["email"]
              : "";
        } else if (key === "userId.mobile") {
          value =
            item["userId"] && item["userId"]["mobile"]
              ? item["userId"]["mobile"]
              : item["userId"] && item["userId"]["mobile"]
              ? item["userId"]["mobile"]
              : "";
        } else if (["totalAmount"].includes(key)) {
          value = value ? `$${amountToShow(value)}` : `$0`;
        } else if (key === "paymentMethodType") {
          value =
            value === "card" ? "Credit Card" : value === "ACH" ? "ACH" : value;
        } else if (key === "isAutoRenew") {
          value = value === true ? "Yes" : "No";
        }
        filteredItem[columnName] = value;
      });
      return filteredItem;
    });

    const ws = XLSX.utils.json_to_sheet(filteredData);

    const columnWidths = Object.keys(columnMapping).map((columnName) => {
      switch (columnName) {
        case "Subscription ID":
          return { wch: 15 };
        case "Start Date":
        case "End Date":
          return { wch: 15 };
        case "Total Amount":
          return { wch: 10 };
        default:
          return { wch: 25 };
      }
    });
    ws["!cols"] = columnWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Sheet1");
    XLSX.writeFile(wb, `${"subscription-report"}.xlsx`);
  };
console.log("subscriptionsList ===>",subscriptionsList)
  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox>
        <MDBox pt={2} pb={3}>
          <Grid container spacing={6}>
            <Grid item xs={12}>
              <Card>
                <MDBox
                  mx={1}
                  mt={-2}
                  py={1}
                  px={1}
                  variant="gradient"
                  bgColor={sidenavColor}
                  borderRadius="lg"
                  coloredShadow={sidenavColor}
                  className="d-flex align-items-center gap-2"
                >
                  <MDTypography
                    variant="h6"
                    color="white"
                    className="flex-grow-1"
                  >
                    Subscriptions
                  </MDTypography>
                </MDBox>
                <MDBox p={2}>
                  <Grid container spacing={4}>
                    <Grid item xs={12} md={2}>
                      <MDButton
                        color={sidenavColor}
                        variant="outlined"
                        size="small"
                        onClick={() => downloadReport(subscriptionsList)}
                      >
                        Export <DownloadIcon />
                      </MDButton>
                    </Grid>
                  </Grid>
                </MDBox>

                <MDBox p={2}>
                  <Grid container spacing={1}>
                    <Grid item xs={12} md={12} lg={12} sx={{ ml: "auto" }}>
                      <AppBar position="static">
                        <Tabs
                          orientation={tabsOrientation}
                          value={tabValue}
                          onChange={handleSetTabValue}
                        >
                          <Tab
                            label="Active"
                            icon={
                              <DirectionsCarIcon
                                fontSize="small"
                                sx={{ mt: -0.25 }}
                              />
                            }
                            value="active"
                          />

                          <Tab
                            label="Canceled"
                            icon={
                              <CancelIcon fontSize="small" sx={{ mt: -0.25 }} />
                            }
                            value="canceled"
                          />

                          <Tab
                            label="Expired"
                            icon={
                              <ExploreOffIcon
                                fontSize="small"
                                sx={{ mt: -0.25 }}
                              />
                            }
                            value="expired"
                          />
                        </Tabs>
                      </AppBar>
                      <TabPanel value={tabValue} index="active">
                        <SubscriptionsTable
                          isLoading={isLoading}
                          subscriptionList={
                            !isEmpty(subscriptionsList)
                              ? sortBy(
                                  subscriptionsList?.filter((item) => {
                                    const startDate = moment(item.startDate);
                                    const endDate = moment(item.endDate).add(
                                      1,
                                      "days"
                                    );
                                    return (
                                      ((item.subscriptionStatus === "active" ||
                                        item.subscriptionStatus === "cancel") &&
                                        currentDate.isBetween(
                                          startDate,
                                          endDate,
                                          null,
                                          "[]"
                                        )) ||
                                      (item.subscriptionStatus === "active" &&
                                        startDate.isAfter(currentDate) &&
                                        endDate.isAfter(currentDate))
                                    );
                                  })
                                )
                              : []
                          }
                          subscriptionType="active"
                        />
                      </TabPanel>

                      <TabPanel value={tabValue} index="canceled">
                        <SubscriptionsTable
                          isLoading={isLoading}
                          subscriptionList={
                            !isEmpty(subscriptionsList)
                              ? subscriptionsList.filter(
                                  (item) => item.subscriptionStatus === "cancel"
                                )
                              : []
                          }
                          subscriptionType="canceled"
                          roleModules={roleModules}
                        />
                      </TabPanel>

                      <TabPanel value={tabValue} index="expired">
                        <SubscriptionsTable
                          isLoading={isLoading}
                          subscriptionList={
                            !isEmpty(subscriptionsList)
                              ? subscriptionsList.filter((item) => {
                                  const endDate = moment(item.endDate);
                                  return (
                                    !item.isSubscriptionPaused &&
                                    currentDate.isAfter(endDate) &&
                                    item.subscriptionStatus !== "pending" &&
                                    item.subscriptionStatus !== "initialize"
                                  );
                                })
                              : []
                          }
                          subscriptionType="expired"
                          roleModules={roleModules}
                        />
                      </TabPanel>
                    </Grid>
                  </Grid>
                </MDBox>
              </Card>
            </Grid>
          </Grid>
        </MDBox>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Subscriptions;
