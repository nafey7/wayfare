import {
  Icon,
  IconButton,
  LinearProgress,
  Stack,
  Switch,
  Tooltip,
} from "@mui/material";
import MDDataGrid from "components/MDDataGrid/MDDataGrid";
import { useState } from "react";
import EmptyTableRowOverlay from "components/MDEmptyOverlay/EmptyTableRowOverlay";
import MDTypography from "components/MDTypography";
import MDProgress from "components/MDProgress";
import MDBox from "components/MDBox";
import { useDispatch, useSelector } from "react-redux";
import { calculatePercentageWithCondition } from "global/functions";
import DeleteDialog from "components/UIComponents/DeleteDialog";
import { deleteRole } from "store/slice/roles/roleSlice";
// import { roleStatusUpdate } from "store/slice/roles/roleSlice";
import PermissionsDialogBox from "./PermissionsDialogBox";
import UpdateRoles from "./UpdateRoles";

const RolesTable = (props) => {
  const dispatch = useDispatch();
  const { rolesData, updateParentData } = props;
  const [page, setPage] = useState(10);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [permissionDialogOpen, setPermissionDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [toggleLoading, setToggleLoading] = useState(null);
  const [rolePermissions, setRolePermissions] = useState(null);
  const [roleId, setRoleId] = useState("");
  const [pageSize, setPageSize] = useState(10);
  const [data, setData] = useState([]);
  const loading = useSelector((state) => state.roles?.loading);


  const handelDelete = () => {
    dispatch(deleteRole({ roleId }))
      .unwrap()
      .then(async (res) => {
        console.log("delete response:", res);
        if (res?.success) {
          updateParentData();
          setDialogOpen(false);
        }
      })
      .catch((err) => {
        console.error("Error getting brand:", err);
      });
  };

  // const handleUpdateRole = (roleId, type) => {
  //   const status = type === "ACTIVE" ? 10 : 1;
  //   setToggleLoading(roleId);
  //   dispatch(roleStatusUpdate({ roleId, status }))
  //     .unwrap()
  //     .then((res) => {
  //       console.log("update response:", res);
  //       if (res?.success) {
  //         updateParentData();
  //       }
  //     })
  //     .catch((err) => {
  //       console.error("Error update:", err);
  //     })
  //     .finally(() => setToggleLoading(null));
  // };

  const columnsData = [
    {
      field: "title",
      headerName: "Role Title",
      width: 155,
      renderCell: ({ row }) => (
        <MDTypography display="block" variant="caption" color="text">
          {row.title}
        </MDTypography>
      ),
    },
    {
      field: "roleLevel",
      headerName: "Role Level",
      width: 220,
      renderCell: ({ row }) => {
        const roleLevel =
          row?.level === 100
            ? 100
            : calculatePercentageWithCondition(row?.modules, true);
        return (
          <MDBox width="11rem" textAlign="left">
            <Tooltip title={`${roleLevel || 0} %`} placeholder="bottom">
              <MDProgress
                value={roleLevel || 0}
                color={
                  roleLevel >= 90
                    ? "success"
                    : roleLevel < 90 && roleLevel >= 50
                    ? "info"
                    : "error"
                }
                variant="gradient"
                label={false}
              />
            </Tooltip>
          </MDBox>
        );
      },
    },

    {
      field: "actions",
      headerName: "Actions",
      width: 200,
      renderCell: ({ row }) => (
        <>
          {!row.default ? (
            <Stack direction="row" alignItems="center">
              <IconButton
                onClick={() => {
                  setDialogOpen(true);
                  setRoleId(row._id);
                }}
                color="error"
              >
                <Icon fontSize="small">delete</Icon>
              </IconButton>
              <Switch
                disabled={toggleLoading === row._id}
                checked={row?.status === 10}
                // onChange={() =>
                //   handleUpdateRole(
                //     row?._id,
                //     row?.status === 10 ? "INACTIVE" : "ACTIVE"
                //   )
                // }
              />
            </Stack>
          ) : null}
          <Tooltip title={"Role Permissions"} placement="top">
            <IconButton
              onClick={() => {
                setPermissionDialogOpen(true);
                setRolePermissions(row.modules);
                setRoleId(row._id);
              }}
              color="success"
            >
              <Icon fontSize="small">accessibility</Icon>
            </IconButton>
          </Tooltip>
          {!row.default ? (
            <Stack direction="row" alignItems="center">
              <IconButton
                onClick={() => {
                  setEditDialogOpen(true);
                  setData(row);
                }}
                color="navbar"
              >
                <Icon fontSize="small">edit</Icon>
              </IconButton>
            </Stack>
          ) : null}
        </>
      ),
    },
  ];

  return (
    <>
      <MDDataGrid
        rows={rolesData ?? []}
        columns={columnsData}
        getRowId={(row) => row?._id}
        pagination
        page={page}
        pageSize={pageSize}
        paginationMode="server"
        onPageChange={(newPage) => setPage(newPage)}
        onPageSizeChange={(newPageSize) => setPageSize(newPageSize)}
        disableSelectionOnClick={true}
        loading={loading}
        components={{
          NoRowsOverlay: EmptyTableRowOverlay,
          LoadingOverlay: LinearProgress,
        }}
      />
      <DeleteDialog
        dialogOpen={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
        }}
        handelClick={handelDelete}
      />
      <PermissionsDialogBox
        dialogOpen={permissionDialogOpen}
        onClose={() => {
          setPermissionDialogOpen(false);
        }}
        PermissionsData={rolePermissions}
      />
      <UpdateRoles
        dialogOpen={editDialogOpen}
        onClose={() => {
          setEditDialogOpen(false);
        }}
        data={data}
      />
    </>
  );
};

export default RolesTable;
