// @mui material components
import Card from "@mui/material/Card";
import Grid from "@mui/material/Grid";
// PMS components
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

// Data
import { useMaterialUIController } from "context";
import { useEffect, useState } from "react";
import UserTable from "./components/UserTable";
import Footer from "examples/Footer";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import { useDispatch, useSelector } from "react-redux";
import { isEmpty } from "lodash";
import {
  getSubscriptions,
  getSubscriptionStatistics,
} from "store/slice/subscriptions/subscriptionSlice";
import { useLocation, useNavigate } from "react-router-dom";
import breakpoints from "assets/theme/base/breakpoints";
import {
  AppBar,
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Tab,
  Tabs,
} from "@mui/material";
import MDDropDown from "components/MDDropDown";
import { getPricingPlans } from "store/slice/pricingPlan/pricingPlanSlice";

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

function SubscriptionPayments() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const activeTab = queryParams.get("tab");

  const [tabsOrientation, setTabsOrientation] = useState("horizontal");
  const [tabValue, setTabValue] = useState(activeTab || "all");

  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;

  const subscriptionsList = useSelector(
    (state) => state.subscriptions?.subscriptions || []
  );
  const pricingPlans = useSelector(
    (state) => state.pricingPlan?.pricingPlans || []
  );

  const [selectedPlan, setSelectedPlan] = useState("");

  useEffect(() => {
    if (isEmpty(subscriptionsList)) {
      dispatch(getSubscriptions());
      dispatch(getSubscriptionStatistics());
    }
  }, [dispatch]);

  useEffect(() => {
    if (isEmpty(pricingPlans)) {
      dispatch(getPricingPlans());
    } else if (!selectedPlan) {
      setSelectedPlan(pricingPlans[0]?._id || "");
    }
  }, [dispatch, pricingPlans]);

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

  const handleSelectedPlanChange = (event) => {
    setSelectedPlan(event.target.value);
  };
  const filteredSubscriptions = selectedPlan
    ? subscriptionsList.filter((user) => user.planId._id == selectedPlan)
    : subscriptionsList;

  return (
    <MDBox>
      <DashboardLayout>
        <DashboardNavbar />

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

                <MDBox p={2} mt={2} maxWidth={250}>
                  <FormControl fullWidth>
                    <InputLabel id="plan-select-label">Select Plan</InputLabel>
                    <MDDropDown
                      labelId="plan-select-label"
                      id="plan-select"
                      label="Select Plan"
                      value={selectedPlan}
                      onChange={handleSelectedPlanChange}
                    >
                      {pricingPlans?.map((plan) => (
                        <MenuItem key={plan._id} value={plan._id}>
                          {plan?.subType}
                        </MenuItem>
                      ))}
                    </MDDropDown>
                  </FormControl>
                </MDBox>

                <MDBox p={2}>
                  <Box>
                    <AppBar position="static">
                      <Tabs
                        orientation={tabsOrientation}
                        value={tabValue}
                        onChange={handleSetTabValue}
                      >
                        <Tab label="All" value="all" />
                        <Tab label="Active" value="active" />
                        <Tab label="Expired" value="expire" />
                        <Tab label="Canceled" value="cancel" />
                      </Tabs>
                    </AppBar>

                    <TabPanel value={tabValue} index={"all"}>
                      <UserTable userData={filteredSubscriptions} />
                    </TabPanel>
                    <TabPanel value={tabValue} index={"active"}>
                      <UserTable userData={filteredSubscriptions} />
                    </TabPanel>
                    <TabPanel value={tabValue} index={"expire"}>
                      <UserTable userData={filteredSubscriptions} />
                    </TabPanel>
                    <TabPanel value={tabValue} index={"cancel"}>
                      <UserTable userData={filteredSubscriptions} />
                    </TabPanel>
                  </Box>
                </MDBox>
              </Card>
            </Grid>
          </Grid>
        </MDBox>

        <Footer />
      </DashboardLayout>
    </MDBox>
  );
}

export default SubscriptionPayments;
