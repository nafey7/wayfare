import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const ProfilePermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Profile_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Profile_view: true,
      }));
    }
  }, [modules, setModules]);

  console.log("modules ====>", modules);

  const handleProfileViewChange = (event) => {
    const isProfileViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Profile_view: isProfileViewEnabled,
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
                Profile Module
              </MDTypography>

              <Tooltip
                title={`${
                  modules.Profile_view ? "Disable" : "Enable"
                } Profile module`}
                placement="top"
              >
                <Switch
                  checked={modules.Profile_view}
                  onChange={handleProfileViewChange}
                />
              </Tooltip>
            </Grid>

          </Grid>
        </MDBox>
      </Card>
    </>
  );
};

export default ProfilePermissionCard;
