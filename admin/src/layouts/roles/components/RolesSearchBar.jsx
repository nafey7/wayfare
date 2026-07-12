import React, { useState, useEffect } from "react";
import Input from "@mui/material/Input";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import ClearIcon from "@mui/icons-material/Clear";

const RolesSearchBar = ({
  rolesList,
  setFilteredRoles,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const filterroles = () => {
      const normalizedSearchTerm = searchTerm.toLowerCase();

      const filtered = rolesList.filter((item) => {
        const { title } = item;
        return (
          title?.toLowerCase().includes(normalizedSearchTerm)
        );
      });

      setFilteredRoles(filtered);
    };

    filterroles();
  }, [searchTerm, setFilteredRoles, rolesList]);

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  const clearSearch = () => {
    setSearchTerm("");
  };

  console.log("filteredroles ---->", rolesList);

  return (
    <>
      <Input
        placeholder="Search"
        value={searchTerm}
        onChange={handleSearch}
        endAdornment={
          <InputAdornment position="end">
            {searchTerm && (
              <IconButton color="secondary" onClick={clearSearch} size="medium">
                <ClearIcon />
              </IconButton>
            )}
            <IconButton color="secondary" size="medium">
              <SearchIcon />
            </IconButton>
          </InputAdornment>
        }
      ></Input>
    </>
  );
};

export default RolesSearchBar;
