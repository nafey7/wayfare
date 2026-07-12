import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const UsersPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.MyUser_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        MyUser_view: true,
        MyUser_add: true,
        MyUser_update: true,
        MyUser_delete: true
      }));
    }
  }, [modules, setModules]);

  console.log("modules ====>", modules);

  const handleUsersViewChange = (event) => {
    const isUsersViewEnabled = event.target.checked;
    setModules({
      ...modules,
      MyUser_view: isUsersViewEnabled,
      ...(isUsersViewEnabled
        ? {}
        : { MyUser_add: false, MyUser_update: false, MyUser_delete: false }),
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
               My User Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.MyUser_view ? "Disable" : "Enable"
                } My User module`}
                placement="top"
              >
                <Switch
                  checked={modules.MyUser_view}
                  onChange={handleUsersViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add MyUser
                  </MDTypography>

                  <Switch
                    checked={modules.MyUser_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        MyUser_add: event.target.checked,
                      })
                    }
                    disabled={!modules.MyUser_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Update MyUser
                  </MDTypography>
                  <Switch
                    checked={modules.MyUser_update}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        MyUser_update: event.target.checked,
                      })
                    }
                    disabled={!modules.MyUser_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete MyUser
                  </MDTypography>
                  <Switch
                    checked={modules.MyUser_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        MyUser_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.MyUser_view}
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

export default UsersPermissionCard;
