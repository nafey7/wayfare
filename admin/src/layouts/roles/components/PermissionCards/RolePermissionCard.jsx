import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const RolePermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Role_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Role_view: true,
        Role_add: true,
        Role_update: true,
        Role_delete: true
      }));
    }
  }, [modules, setModules]);

  console.log("modules ====>", modules);

  const handleRoleViewChange = (event) => {
    const isRoleViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Role_view: isRoleViewEnabled,
      ...(isRoleViewEnabled
        ? {}
        : { Role_add: false, Role_update: false, Role_delete: false }),
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
                Role Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.Role_view ? "Disable" : "Enable"
                } Role module`}
                placement="top"
              >
                <Switch
                  checked={modules.Role_view}
                  onChange={handleRoleViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={2.5}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add Role
                  </MDTypography>

                  <Switch
                    checked={modules.Role_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Role_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Role_view}
                  />
                </Grid>

                <Grid item xs={6} md={4}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Active / Deactive Role
                  </MDTypography>
                  <Switch
                    checked={modules.Role_update}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Role_update: event.target.checked,
                      })
                    }
                    disabled={!modules.Role_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete Role
                  </MDTypography>
                  <Switch
                    checked={modules.Role_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Role_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.Role_view}
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

export default RolePermissionCard;
