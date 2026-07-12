import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const ContentPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Content_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Content_view: true,
        Content_add: true,
        Content_delete: true,
      }));
    }
  }, [modules, setModules]);

  const handleContentsViewChange = (event) => {
    const isContentsViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Content_view: isContentsViewEnabled,
      ...(isContentsViewEnabled
        ? {}
        : { Content_add: false, Content_delete: false }),
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
                Content Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.Content_view ? "Disable" : "Enable"
                } Content module`}
                placement="top"
              >
                <Switch
                  checked={modules.Content_view}
                  onChange={handleContentsViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add Content
                  </MDTypography>

                  <Switch
                    checked={modules.Content_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Content_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Content_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete Content
                  </MDTypography>
                  <Switch
                    checked={modules.Content_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Content_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.Content_view}
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

export default ContentPermissionCard;
