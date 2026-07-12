import MDBox from "components/MDBox";
import DefaultSortInfoCard from "examples/Cards/InfoCards/DefaultInfoCard/DefaultSortInfoCard";
import React from "react";
import { useMaterialUIController } from "context";
import Grid from "@mui/material/Grid";

const Statistics = ({ data }) => {
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;

  return (
    <>
      <MDBox>
        <Grid container alignItems="center" spacing={2}>
          <Grid item md={3} xs={12}>
            <DefaultSortInfoCard
              color={sidenavColor}
              icon="subscriptions"
              title="Total Subscriptions"
              value={`${data?.totalSubscriptions || 0}`}
            />
          </Grid>
          {/* <Grid item xs={12} md={3}>
            <DefaultSortInfoCard
              color={sidenavColor}
              icon="real_estate_agent"
              title="Active Subscriptions"
              value={`${data?.activeSubscriptions || 0}`}
            />
          </Grid> */}
          <Grid item xs={12} md={3}>
            <DefaultSortInfoCard
              color={sidenavColor}
              icon="peoples"
              title="Total Users"
              value={`${data?.totalUsers || 0}`}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <DefaultSortInfoCard
              color={sidenavColor}
              icon="book_online"
              title="Without Subscribed User"
              value={`${data?.withoutSubscribedUser || 0}`}
            />
          </Grid>
        </Grid>
      </MDBox>
    </>
  );
};

export default Statistics;
