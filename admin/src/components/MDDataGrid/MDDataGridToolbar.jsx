import React from "react";
import PropTypes from "prop-types";
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
} from "@mui/x-data-grid";

const MDDataGridToolbar = (props) => {
  const theme = useTheme();

  const {
    DisableToolbarColumnsButton,
    DisableToolbarFilterButton,
    DisableToolbarDensitySelector,
    DisableToolbarExport,
    disableTools,
    align,
    divider,
    children,
  } = props;

  return (
    <>
      <GridToolbarContainer
        sx={{
          "& .root-MuiDataGrid-paper": { maxWidth: "280px" },
        }}
      >
        <Box
          component="div"
          sx={{ width: "100%", py: 1 }}
          className={divider && "border-bottom"}
        >
          <Grid
            container
            spacing={2}
            sx={{ justifyContent: "space-between", flexWrap: "wrap" }}
          >
            {!disableTools && (
              <Grid item sm={disableTools ? 0 : 6} xs={12}>
                <Stack
                  direction="row"
                  alignItems="center"
                  // flexWrap="wrap"
                  justifyContent={{ md: "flex-start", xs: "space-evenly" }}
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
                        [theme.breakpoints.down("md")]: {
                          // width: "45%",
                          flexDirection: "column",
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
                        [theme.breakpoints.down("md")]: {
                          // width: "45%",
                          flexDirection: "column",
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
                        [theme.breakpoints.down("md")]: {
                          // width: "45%",
                          flexDirection: "column",
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
                        [theme.breakpoints.down("md")]: {
                          // width: "45%",
                          flexDirection: "column",
                        },
                      }}
                    />
                  )}
                </Stack>
              </Grid>
            )}
            {children ? (
              <Grid item sm={disableTools ? 12 : 6} xs={12}>
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
