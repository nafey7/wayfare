import React, { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";

import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import SyncIcon from "@mui/icons-material/Sync";

const SUBMIT_FILTER_STROKE_TIME = 500;

const InputNumberInterval = (props) => {
  const { item, applyValue, type, focusElementRef = null } = props;

  const filterTimeout = useRef();
  const [filterValueState, setFilterValueState] = useState(item?.value ?? "");

  const [applying, setIsApplying] = useState(false);

  useEffect(() => {
    return () => {
      clearTimeout(filterTimeout.current);
    };
  }, []);

  useEffect(() => {
    const itemValue = item.value ?? ["", ""];
    setFilterValueState(itemValue);
  }, [item.value]);

  const updateFilterValue = (lowerBound, upperBound) => {
    clearTimeout(filterTimeout.current);
    setFilterValueState([lowerBound, upperBound]);

    setIsApplying(true);
    filterTimeout.current = setTimeout(() => {
      setIsApplying(false);
      applyValue({ ...item, value: [lowerBound, upperBound] });
    }, SUBMIT_FILTER_STROKE_TIME);
  };

  const handleUpperFilterChange = (event) => {
    const newUpperBound = event.target.value;
    updateFilterValue(filterValueState[0], newUpperBound);
  };
  const handleLowerFilterChange = (event) => {
    const newLowerBound = event.target.value;
    updateFilterValue(newLowerBound, filterValueState[1]);
  };

  return (
    <Box
      sx={{
        display: "inline-flex",
        flexDirection: "row",
        alignItems: "end",
        height: 48,
      }}
    >
      <TextField
        name="lower-bound-input"
        placeholder="From"
        label="From"
        variant="standard"
        value={filterValueState[0]}
        onChange={handleLowerFilterChange}
        type={type}
        inputRef={focusElementRef}
        fullWidth={true}
        InputLabelProps={{ shrink: true }}
        sx={{ mr: 1 }}
      />
      <TextField
        name="upper-bound-input"
        placeholder="To"
        label="To"
        variant="standard"
        value={filterValueState[1]}
        onChange={handleUpperFilterChange}
        type={type}
        InputProps={applying ? { endAdornment: <SyncIcon /> } : {}}
        fullWidth={true}
        InputLabelProps={{ shrink: true }}
      />
    </Box>
  );
};

InputNumberInterval.propTypes = {
  applyValue: PropTypes.func.isRequired,
  // focusElementRef: PropTypes.oneOfType([
  //   PropTypes.func,
  //   PropTypes.shape({
  //     current: PropTypes.any.isRequired,
  //   }),
  // ]),
  item: PropTypes.shape({
    columnField: PropTypes.string.isRequired,
    id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]),
    operatorValue: PropTypes.string,
    value: PropTypes.any,
  }).isRequired,
};

const QuantityOnlyOperator = ({ inputType }) => [
  {
    label: "Between",
    value: "range",
    getApplyFilterFn: (filterItem) => {
      if (!Array.isArray(filterItem.value) || filterItem.value.length !== 2) {
        return null;
      }
      if (filterItem.value[0] == null || filterItem.value[1] == null) {
        return null;
      }

      return ({ value }) => {
        return (
          value !== null &&
          filterItem.value[0] <= value &&
          value <= filterItem.value[1]
        );
      };
    },
    InputComponent: InputNumberInterval,
    InputComponentProps: { type: inputType ?? "text" },
  },
];
QuantityOnlyOperator.propTypes = {
  inputType: PropTypes.string.isRequired,
};
export default QuantityOnlyOperator;
