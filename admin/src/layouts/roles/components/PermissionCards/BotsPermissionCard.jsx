import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const BotsPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Bots_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Bots_view: true,
        Bots_add: true,
        BotFlows_add: true,
        Bots_delete: true,
      }));
    }
  }, [modules, setModules]);

  const handleBotsViewChange = (event) => {
    const isBotsViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Bots_view: isBotsViewEnabled,
      ...(isBotsViewEnabled
        ? {}
        : { Bots_add: false, BotFlows_add: false, Bots_delete: false }),
    });
  };

  return (
    <>
      <Card sx={{ minWidth: 275, boxShadow: 3 }}>
        <MDBox p={2}>
          <Grid container spacing={1}>
            <Grid item xs={12} container alignItems="center">
              <MDTypography
                color="dark"
                display="block"
                variant="subtitle2"
                fontWeight="bold"
                sx={{ flex: 1 }}
              >
                Bots Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.Bots_view ? "Disable" : "Enable"
                } Bots module`}
                placement="top"
              >
                <Switch
                  checked={modules.Bots_view}
                  onChange={handleBotsViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add Bots
                  </MDTypography>

                  <Switch
                    checked={modules.Bots_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Bots_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Bots_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete Bots
                  </MDTypography>
                  <Switch
                    checked={modules.Bots_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Bots_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.Bots_view}
                  />
                </Grid>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Bot Flow Add
                  </MDTypography>
                  <Switch
                    checked={modules.BotFlows_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        BotFlows_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Bots_view}
                  />
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </MDBox>
      </Card>
    </>
  );
};

export default BotsPermissionCard;
