import React from "react";
import { useTheme } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";

const MDDataGrid = (props) => {
  const { sx, ...rest } = props;

  const theme = useTheme();

  return (
    <>
      <DataGrid
        {...rest}
        GridSlotsComponentsProps={{
          panel: {
            sx: {
              "& .MuiDataGrid-paper": {
                "& .MuiDataGrid-filterForm": {
                  "& .MuiDataGrid-filterFormOperatorInput": {
                    marginLeft: 1,
                  },
                  "& .MuiDataGrid-filterFormValueInput": {
                    width: "auto",
                    marginLeft: 1,
                  },
                },
              },
              [theme.breakpoints.down("sm")]: {
                "& .MuiDataGrid-paper": {
                  margin: 1,
                  "& .MuiDataGrid-filterForm": {
                    flexWrap: "wrap",
                    gap: "8px",
                    "& .MuiDataGrid-filterFormDeleteIcon": {
                      justifyContent: "center",
                    },
                    "& .MuiDataGrid-filterFormColumnInput": {
                      width: "calc(100% - 45px)",
                    },
                    "& .MuiDataGrid-filterFormOperatorInput,& .MuiDataGrid-filterFormValueInput":
                      {
                        width: "100%",
                        marginLeft: 0,
                      },
                  },
                },
              },
            },
          },
        }}
        sx={{
          minHeight: "400px",
          border: "none",
          "& .MuiDataGrid-columnHeader,.MuiDataGrid-cell": {
            ":focus": {
              outline: "none",
            },
          },
          "& .MuiDataGrid-columnHeader--sorted,& .MuiDataGrid-columnHeader--filtered,& .MuiDataGrid-columnHeader--sortable":
            {
              ":focus-within": { outline: "none" },
            },
          "& .MuiDataGrid-virtualScroller": {
            "& .MuiDataGrid-virtualScrollerContent": {
              minHeight: "280px !important",
            },
          },
          ...sx,
        }}
      />
    </>
  );
};

MDDataGrid.propTypes = {};

export default MDDataGrid;
