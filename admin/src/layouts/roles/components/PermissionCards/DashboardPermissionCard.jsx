import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const DashboardPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Dashboard_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Dashboard_view: true,
      }));
    }
  }, [modules, setModules]);

  console.log("modules ====>", modules);

  const handleDashboardViewChange = (event) => {
    const isDashboardViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Dashboard_view: isDashboardViewEnabled,
    });
  };

  return (
    <>
      <Card sx={{ minWidth: 275, boxShadow: 3 }}>
        <MDBox p={2}>
          <Grid container spacing={1}>
            <Grid item lg={12} md={12} xs={12} container alignItems="center">
              <MDTypography
                color="dark"
                display="block"
                variant="subtitle2"
                fontWeight="bold"
                sx={{ flex: 1 }}
              >
                Dashboard Module
              </MDTypography>

              <Tooltip
                title={`${
                  modules.Dashboard_view ? "Disable" : "Enable"
                } Dashboard module`}
                placement="top"
              >
                <Switch
                  checked={modules.Dashboard_view}
                  onChange={handleDashboardViewChange}
                />
              </Tooltip>
            </Grid>

          </Grid>
        </MDBox>
      </Card>
    </>
  );
};

export default DashboardPermissionCard;
