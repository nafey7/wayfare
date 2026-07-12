import MDBox from "components/MDBox";
import DashboardLayout from "examples/LayoutContainers/DashboardLayout";
import DashboardNavbar from "examples/Navbars/DashboardNavbar";
import Footer from "examples/Footer";
import ComplexStatisticsCard from "examples/Cards/StatisticsCards/ComplexStatisticsCard";
import { Grid } from "@mui/material";
import { useDispatch, useSelector } from "react-redux";
import { getStatistics } from "store/slice/dashboard/dashboardSlice";
import { isEmpty } from "lodash";
import { useEffect } from "react";

function Dashboard() {
  const dispatch = useDispatch();

  const statistics = useSelector((state) => state.dashboard.statistics);

  useEffect(() => {
    if (isEmpty(statistics)) {
      dispatch(getStatistics());
    }
  }, [dispatch]);
  return (
    <DashboardLayout>
      <DashboardNavbar />
      <MDBox py={3}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6} lg={3}>
            <MDBox mb={1.5}>
              <ComplexStatisticsCard
                color="dark"
                icon="peoples"
                title="Total Visiters"
                count={statistics.totalVisiters||0}
                percentage={{
                  color: "success",
                  amount: `${10 > 0 ? "+" : ""}${10 || 0}%`,
                  label: `${10 > 0 ? "greater" : "less"} than last month`,
                }}
              />
            </MDBox>
          </Grid>
          <Grid item xs={12} md={6} lg={3}>
            <MDBox mb={1.5}>
              <ComplexStatisticsCard
                color="success"
                icon="person"
                title="Total Users"
                count={statistics.totalUsers||0}
                percentage={{
                  color: 100 > 0 ? "success" : "error",
                  amount: `${100 > 0 ? "+" : ""}${100 || 0}%`,
                  label: `${100 > 0 ? "greater" : "less"} than last month`,
                }}
              />
            </MDBox>
          </Grid>
          <Grid item xs={12} md={6} lg={3}>
            <MDBox mb={1.5}>
              <ComplexStatisticsCard
                color="primary"
                icon="task"
                title="Subscribed Users"
                count={statistics.activeSubscriptions||0}
                percentage={{
                  color: 100 > 0 ? "success" : "error",
                  amount: `${100 > 0 ? "+" : ""}${100 || 0}%`,
                  label: `${100 > 0 ? "greater" : "less"} than last month`,
                }}
              />
            </MDBox>
          </Grid>
          <Grid item xs={12} md={6} lg={3}>
            <MDBox mb={1.5}>
              <ComplexStatisticsCard
                color="primary"
                icon="task"
                title="Without Subscribed Users"
                count={statistics.withoutSubscribedUser||0}
                percentage={{
                  color: 100 > 0 ? "success" : "error",
                  amount: `${100 > 0 ? "+" : ""}${100 || 0}%`,
                  label: `${100 > 0 ? "greater" : "less"} than last month`,
                }}
              />
            </MDBox>
          </Grid>
        </Grid>
      </MDBox>
      <Footer />
    </DashboardLayout>
  );
}

export default Dashboard;
