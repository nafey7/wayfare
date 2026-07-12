import MDDialog from "components/MDDialog";
import React from "react";
import { DialogContent } from "@mui/material";
import { useMaterialUIController } from "context";
import MDBadge from "components/MDBadge";

const LicensePlatesDialog = (props) => {
  const { dialogOpen, onClose, licensePlates } = props;
  const [controller] = useMaterialUIController();
  const { sidenavColor } = controller;
  return (
    <>
      <MDDialog
        dialogTitle="All License Plates"
        open={dialogOpen}
        dialogClose={onClose}
        closeIcon={true}
        maxWidth="sm"
      >
        <DialogContent>
          <div>
            {licensePlates.map((plate) => (
              <MDBadge
                key={plate._id}
                badgeContent={plate.licensePlateNumber}
                color={sidenavColor}
                variant="gradient"
                size="sm"
                sx={{ marginRight: 1 }}
              />
            ))}
          </div>
        </DialogContent>
      </MDDialog>
    </>
  );
};

export default LicensePlatesDialog;
