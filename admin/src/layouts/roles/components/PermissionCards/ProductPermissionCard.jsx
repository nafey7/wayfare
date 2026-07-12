import React, { useEffect } from "react";
import { Grid, Card, Switch, Tooltip } from "@mui/material";
import MDBox from "components/MDBox";
import MDTypography from "components/MDTypography";

const ProductPermissionCard = (props) => {
  const { modules, setModules } = props;
  useEffect(() => {
    if (modules.Product_view === undefined) {
      setModules((prevModules) => ({
        ...prevModules,
        Product_view: true,
        Product_add: true,
        Product_update: true,
        Product_delete: true
      }));
    }
  }, [modules, setModules]);


  const handleProductsViewChange = (event) => {
    const isProductsViewEnabled = event.target.checked;
    setModules({
      ...modules,
      Product_view: isProductsViewEnabled,
      ...(isProductsViewEnabled
        ? {}
        : { Product_add: false, Product_update: false, Product_delete: false }),
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
               Product Module
              </MDTypography>
              <Tooltip
                title={`${
                  modules.Product_view ? "Disable" : "Enable"
                } Product module`}
                placement="top"
              >
                <Switch
                  checked={modules.Product_view}
                  onChange={handleProductsViewChange}
                />
              </Tooltip>
            </Grid>

            <Grid item xs={12}>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Add Product
                  </MDTypography>

                  <Switch
                    checked={modules.Product_add}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Product_add: event.target.checked,
                      })
                    }
                    disabled={!modules.Product_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Update Product
                  </MDTypography>
                  <Switch
                    checked={modules.Product_update}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Product_update: event.target.checked,
                      })
                    }
                    disabled={!modules.Product_view}
                  />
                </Grid>

                <Grid item xs={6} md={3}>
                  <MDTypography variant="caption" fontWeight="regular">
                    Delete Product
                  </MDTypography>
                  <Switch
                    checked={modules.Product_delete}
                    onChange={(event) =>
                      setModules({
                        ...modules,
                        Product_delete: event.target.checked,
                      })
                    }
                    disabled={!modules.Product_view}
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

export default ProductPermissionCard;
