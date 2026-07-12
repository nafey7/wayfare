import React from "react";

import { styled } from "@mui/material/styles";
import InputBase from "@mui/material/InputBase";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import ClearIcon from "@mui/icons-material/Clear";

import { Formik } from "formik";
import { useSelector } from "react-redux";
import { isEmpty } from "lodash";
import { useMaterialUIController } from "context";

const SearchBar = (props) => {
  const [controller] = useMaterialUIController();
  const { darkMode } = controller;
  const { setFilterOptions, filterOptions } = props;
  const loading = useSelector((state) => state?.transactions?.loading || false);
  const StyledInputBase = styled(InputBase)(({ theme }) => ({
    width: "100%",
    margin: "auto",
    borderRadius: theme.spacing(1),
    paddingLeft: theme.spacing(2.5),
    border: `1px solid ${theme.palette.grey[300]}`,
    animation: "all 0.3s ease-in-out",
    "& .MuiInputBase-input": {
      minHeight: theme.spacing(4),
      color: darkMode ? "#ffffff" : "#1c1c1c",
    },
    "& .MuiInputAdornment-root": {
      minHeight: theme.spacing(5),
    },
    "& .MuiIconButton-root": {
      padding: `${theme.spacing(1)} ${theme.spacing(1.5)}`,
      borderRadius: "0 50% 50% 0",
      "& .MuiTouchRipple-child": {
        borderRadius: "0 50% 50% 0",
      },
    },
    "&.Mui-focused": {
      borderColor: theme.palette.secondary.main,
      "& .MuiInputAdornment-root": {
        borderColor: theme.palette.secondary.main,
      },
    },
  }));

  return (
    <>
      <Formik
        initialValues={{
          search: "",
        }}
        onSubmit={(values) => {
          setFilterOptions({ ...filterOptions, pageNo: 0, ...values });
        }}
      >
        {(props) => (
          <form onSubmit={props.handleSubmit}>
            <StyledInputBase
              placeholder="Search"
              name="search"
              value={props.values.search}
              onChange={props.handleChange}
              sx={{ maxWidth: { xs: "300px", sm: "650px" } }}
              inputProps={{ "aria-label": "search articles" }}
              endAdornment={
                <InputAdornment position="end">
                  {props.values.search && (
                    <IconButton
                      color="secondary"
                      size="medium"
                      onClick={() => {
                        props.setFieldValue("search", "");
                        setFilterOptions({
                          ...filterOptions,
                          pageNo: 0,
                          search: "",
                        });
                      }}
                    >
                      <ClearIcon fontSize="inherit" color="text" />
                    </IconButton>
                  )}

                  <IconButton
                    color="secondary"
                    size="medium"
                    type="submit"
                    className="border-left"
                    disabled={
                      isEmpty(props.values.search) ||
                      (props.isSubmitting && loading)
                    }
                  >
                    <SearchIcon fontSize="medium" color="text" />
                  </IconButton>
                </InputAdornment>
              }
            />
          </form>
        )}
      </Formik>
    </>
  );
};

export default SearchBar;
