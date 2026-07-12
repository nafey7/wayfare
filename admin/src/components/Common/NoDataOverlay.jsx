import React from "react";

import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";

import NoDataOverlyImg from "../../assets/images/undraw_no_data.svg";

const NoDataOverlay = () => {
  return (
    <Paper className="w-100 h-100">
      <CardContent className="w-100 h-100">
        <Box className="w-100 h-100 d-flex flex-column justify-content-center align-items-center gap-3">
          <Box component="img" src={NoDataOverlyImg} sx={{width: '150px', height: '150px'}}/>
          <Typography variant="body1" fontSize="1.125rem" color="grey.600">
            No Data
          </Typography>
        </Box>
      </CardContent>
    </Paper>
  );
};

export default NoDataOverlay;
