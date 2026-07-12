import React from "react";
import PropTypes from "prop-types";
import { isEmpty } from "lodash";

import { useTheme } from "@mui/material";
import Box from "@mui/material/Box";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";

import {
  GridToolbarContainer,
  GridToolbarColumnsButton,
  GridToolbarFilterButton,
  GridToolbarDensitySelector,
  GridToolbarExport,
  GridToolbarQuickFilter,
} from "@mui/x-data-grid";

const MDDataGridToolbar = (props) => {
  const theme = useTheme();

  const {
    DisableToolbarColumnsButton,
    DisableToolbarFilterButton,
    DisableToolbarDensitySelector,
    DisableToolbarExport,
    ToolbarQuickFilter,
    disableTools,
    align,
    divider,
    children,
  } = props;

  return (
    <>
      <GridToolbarContainer>
        <Box
          component="div"
          sx={{ width: "100%", pb: 1 }}
          className={divider && "border-bottom"}
        >
          <Grid
            container
            spacing={2}
            sx={{
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            {!disableTools && (
              <Grid
                item
                sm={disableTools ? 0 : isEmpty(children) ? 12 : 8}
                xs={12}
              >
                <Box>
                  <Stack
                    direction={{ md: "row", xs: "column" }}
                    alignItems={{ md: "center", xs: "stretch" }}
                    justifyContent="space-between"
                    spacing={1}
                  >
                    <Box>
                      <Stack
                        direction="row"
                        alignItems="center"
                        justifyContent={{
                          sm: "flex-start",
                          xs: children ? "space-between" : "flex-start",
                        }}
                        spacing={1}
                      >
                        {!DisableToolbarColumnsButton && (
                          <GridToolbarColumnsButton
                            sx={{
                              flexWrap: "wrap",
                              [theme.breakpoints.up("md")]: {
                                mr: 1,
                                px: 1,
                                fontSize: ".875rem",
                              },
                            }}
                          />
                        )}
                        {!DisableToolbarFilterButton && (
                          <GridToolbarFilterButton
                            sx={{
                              flexWrap: "wrap",
                              [theme.breakpoints.up("md")]: {
                                mr: 1,
                                px: 1,
                                fontSize: ".875rem",
                              },
                            }}
                          />
                        )}
                        {!DisableToolbarDensitySelector && (
                          <GridToolbarDensitySelector
                            sx={{
                              flexWrap: "wrap",
                              [theme.breakpoints.up("md")]: {
                                mr: 1,
                                px: 1,
                                fontSize: ".875rem",
                              },
                            }}
                          />
                        )}
                        {!DisableToolbarExport && (
                          <GridToolbarExport
                            sx={{
                              flexWrap: "wrap",
                              [theme.breakpoints.up("md")]: {
                                mr: 1,
                                px: 1,
                                fontSize: ".875rem",
                              },
                            }}
                          />
                        )}
                      </Stack>
                    </Box>
                    {ToolbarQuickFilter && (
                      <Box>
                        <GridToolbarQuickFilter
                          sx={{
                            flexWrap: "wrap",
                            width: "100%",
                            [theme.breakpoints.up("md")]: {
                              mr: 1,
                              px: 1,
                              fontSize: ".875rem",
                            },
                          }}
                        />
                      </Box>
                    )}
                  </Stack>
                </Box>
              </Grid>
            )}
            {children ? (
              <Grid item sm={disableTools ? 12 : 4} xs={12}>
                <Box className={`text-${align}`}>{children}</Box>
              </Grid>
            ) : null}
          </Grid>
        </Box>
      </GridToolbarContainer>
    </>
  );
};

MDDataGridToolbar.propTypes = {
  DisableToolbarColumnsButton: PropTypes.bool,
  DisableToolbarFilterButton: PropTypes.bool,
  DisableToolbarDensitySelector: PropTypes.bool,
  DisableToolbarExport: PropTypes.bool,
  children: PropTypes.node,
};

export default MDDataGridToolbar;
