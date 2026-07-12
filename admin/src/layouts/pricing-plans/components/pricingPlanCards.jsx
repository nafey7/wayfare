import { LoadingButton, TabContext, TabList, TabPanel } from "@mui/lab";
import {
  AppBar,
  Box,
  Card,
  CardActions,
  CardContent,
  Tab,
  Tabs,
  Typography,
  styled,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import { useEffect, useState } from "react";
import { centsToDollars } from "global/functions";
import { useMaterialUIController } from "context";
import MDBox from "components/MDBox";
import { useLocation, useNavigate } from "react-router-dom";
import breakpoints from "assets/theme/base/breakpoints";

const PricingPlansCards = (props) => {
  const { plans } = props;
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  const [value, setValue] = useState("1");
  const [tabsOrientation, setTabsOrientation] = useState("horizontal");
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  const activeTab = queryParams.get("tab");
  const [tabValue, setTabValue] = useState(activeTab || "1");
  const [selectedPlanId, setSelectedPlanId] = useState("");

  const handleChange = (event, newValue) => setValue(newValue);

  const StyledTabList = styled(TabList)(({ theme }) => ({
    "& .MuiTab-root": {
      textTransform: "none",
      color: theme.palette.text.secondary,
      fontWeight: theme.typography.fontWeightMedium,
      "&.Mui-selected": {
        color: theme.palette.text.secondary,
        fontWeight: theme.typography.fontWeightBold,
      },
      "&:hover": {
        color: theme.palette.text.secondary,
      },
    },
    "& .MuiTabs-indicator": {
      backgroundColor: theme.palette.primary.secondary,
    },
  }));

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
  console.log("sidenavColor ===>", sidenavColor);
  const PlanCard = ({ plans }) => (
    <>
      {plans.map((plan) => (
        <Card
          sx={{
            maxWidth: 250,
            // backgroundColor:"",
            borderRadius: "15px",
            padding: "16px",
            boxShadow: "0px 4px 10px rgba(0,0,0,0.3)",
          }}
        >
          <CardContent>
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              {plan.title}
            </Typography>
            <Typography variant="h4" fontWeight="bold">
              ${centsToDollars(plan.price)}
              <Typography variant="body1" component="span">
                / Month
              </Typography>
            </Typography>
            <Typography variant="body2" color="rgb(31, 41, 55)" gutterBottom>
              Select our {plan.title} plan to access our services
            </Typography>
            <Box sx={{ marginY: 2 }}>
              {plan?.features?.map((feature) => (
                <Box
                  key={feature}
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    marginBottom: "8px",
                  }}
                >
                  <CheckCircleIcon
                    sx={{
                      fontSize: 20,
                      color: "rgb(31, 41, 55)",
                      marginRight: "8px",
                    }}
                  />
                  <Typography color="text.main" variant="body2">
                    {feature}
                  </Typography>
                </Box>
              ))}
            </Box>
          </CardContent>
        </Card>
      ))}
    </>
  );

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

  return (
    <>
      <Box>
        <AppBar position="static">
          <Tabs
            orientation={tabsOrientation}
            value={tabValue}
            onChange={handleSetTabValue}
          >
            <Tab label="Individual" value="1" />
            <Tab label="Enterprise" value="2" />
            <Tab label="Flexible" value="3" />
          </Tabs>
        </AppBar>
        <TabPanel value={tabValue} index={"1"}>
          <Box display="flex" gap={2} flexWrap="wrap">
            <PlanCard
              plans={plans.filter((plan) => plan.type === "Individual")}
            />
          </Box>
        </TabPanel>
        <TabPanel value={tabValue} index={"2"}>
          <Box display="flex" gap={2} flexWrap="wrap">
            <PlanCard
              plans={plans.filter((plan) => plan.type === "Enterprise")}
            />
          </Box>
        </TabPanel>
        <TabPanel value={tabValue} index={"3"}>
          <Box display="flex" gap={2} flexWrap="wrap">
            <PlanCard
              plans={plans.filter((plan) => plan.type === "Flexible")}
            />
          </Box>
        </TabPanel>
      </Box>
    </>
  );
};

export default PricingPlansCards;
