import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const CategoryPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Category_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Category_view: true,
        Category_add: true,
        Category_update: true,
        Category_delete: true
      }));
    }
  }, [modules, setModules]);


  const handleCategorysViewChange = (event) => {
    const isCategorysViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Category_view: isCategorysViewEnabled,
      ...(isCategorysViewEnabled
        ? {}
        : { Category_add: false, Category_update: false, Category_delete: false }),
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
               Category Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.Category_view ? "Disable" : "Enable"
                } Category module`}
                placement="top"
              >
                <Switch
                  checked={modules.Category_view}
                  onChange={handleCategorysViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add Category
                  </MDTypography>

                  <Switch
                    checked={modules.Category_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Category_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Category_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Update Category
                  </MDTypography>
                  <Switch
                    checked={modules.Category_update}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Category_update: event.target.checked,
                      })
                    }
                    disabled={!modules.Category_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete Category
                  </MDTypography>
                  <Switch
                    checked={modules.Category_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Category_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.Category_view}
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

export default CategoryPermissionCard;
