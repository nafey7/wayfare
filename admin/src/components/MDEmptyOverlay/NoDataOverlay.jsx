import React from "react";

import CardContent from "@mui/material/CardContent";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import MDCard from "components/md-components/card/MDCard";
import { ReactComponent as NoDataOverly } from "assets/images/undraw_no_data.svg";

const NoDataOverlay = () => {
  return (
    <MDCard className="w-100 h-100 min-h-25">
      <CardContent className="w-100 h-100">
        <Box className="w-100 h-100 d-flex flex-column justify-content-center align-items-center gap-3">
          <NoDataOverly width="150px" height="150px" />
          <Typography variant="body1" fontSize="1.125rem" color="grey.600">
            No Data
          </Typography>
        </Box>
      </CardContent>
    </MDCard>
  );
};

export default NoDataOverlay;
