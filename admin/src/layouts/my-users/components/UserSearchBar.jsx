import React, { useState, useEffect } from "react";
import Input from "@mui/material/Input";
import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import ClearIcon from "@mui/icons-material/Clear";

const UserSearchBar = ({
  usersListData,
  setUserFilteredData,
}) => {
  const [searchTerm, setSearchTerm] = useState("");

  useEffect(() => {
    const filteruser = () => {
      const normalizedSearchTerm = searchTerm.toLowerCase();

      const filtered = usersListData.filter((item) => {
        const { firstName, lastName, mobile, roleId, locations
        } = item;
        const fullName = `${firstName ?? ""} ${lastName ?? ""}`
          .toLowerCase()
          .trim();
        return (
          fullName.includes(normalizedSearchTerm) ||
          firstName?.toLowerCase().includes(normalizedSearchTerm) ||
          lastName?.toLowerCase().includes(normalizedSearchTerm) ||
          mobile?.toLowerCase().includes(normalizedSearchTerm) ||
          roleId?.title?.toLowerCase().includes(normalizedSearchTerm) ||
          locations?.some((location) =>
            location.parkingCode
              .toLowerCase()
              .includes(normalizedSearchTerm)
          )
        );
      });

      setUserFilteredData(filtered);
    };

    filteruser();
  }, [searchTerm, setUserFilteredData, usersListData]);

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  const clearSearch = () => {
    setSearchTerm("");
  };

  console.log("filteredUser ---->", usersListData);

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

export default UserSearchBar;
