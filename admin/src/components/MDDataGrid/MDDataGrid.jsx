import React from "react";
import { useTheme } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { useMaterialUIController } from "context";

const MDDataGrid = (props) => {
  const { sx, ...rest } = props;

  const theme = useTheme();
  const [controller] = useMaterialUIController();
  const { darkMode } = controller;

  return (
    <>
      <DataGrid
        {...rest}
        slotProps={{
          panel: {
            sx: {
              [theme.breakpoints.down("sm")]: {
                "& .MuiDataGrid-paper": {
                  margin: 1,
                  "& .MuiDataGrid-filterForm": {
                    flexWrap: "wrap",
                    gap: "8px",
                    "& .MuiDataGrid-filterFormDeleteIcon": {
                      justifyContent: "center",
                    },
                    "& .MuiDataGrid-filterFormColumnInput": { width: "85%" },
                    "& .MuiDataGrid-filterFormOperatorInput,& .MuiDataGrid-filterFormValueInput":
                      {
                        width: "100%",
                      },
                  },
                },
              },
            },
          },
        }}
        sx={{
          border: 0.5,
          fontSize: "12px",
          borderColor: `${theme.palette.grey[200]}`,
          boxShadow: "none",
          color: darkMode ? "#ffffff" : "#1c1c1c",
          "& .MuiDataGrid-columnHeader,.MuiDataGrid-cell": {
            ":focus": {
              outline: "none",
            },
          },
          "& .MuiDataGrid-columnHeader--sorted:,& .MuiDataGrid-columnHeader--filtered,& .MuiDataGrid-columnHeader--sortable":
            {
              ":focus-within": { outline: "none" },
            },
          "& .MuiDataGrid-sortIcon": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },
          "& .MuiTypography-root": {
            color: darkMode ? "#ffffff" : "#000000",
            fontWeight: "400",
          },
          "& .MuiDataGrid-menuIconButton": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },
          "& .MuiTablePagination-selectLabel": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },
          "& .MuiTablePagination-input": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },
          "& .MuiTablePagination-displayedRows": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },
          "& .MuiSvgIcon-root": {
            color: darkMode ? "#ffffff" : "#1c1c1c",
          },

          ...sx,
        }}
      />
    </>
  );
};

MDDataGrid.propTypes = {};

export default MDDataGrid;
