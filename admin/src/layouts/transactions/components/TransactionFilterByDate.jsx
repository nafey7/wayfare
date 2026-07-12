import { Formik } from "formik";
import moment from "moment";
import React from "react";
import { FormControl } from "@mui/material";
import DateRangePicker from "rsuite/DateRangePicker";
import { useSelector } from "react-redux";

const TransactionFilterByDate = (props) => {
  const selectedPlace = useSelector((state) => state.places?.selectedPlace);
  const placeId = selectedPlace?._id;
  const { filterOptions, setFilterOptions } = props;
  return (
    <>
      <Formik
        initialValues={{
          startDate: "",
          endDate: "",
        }}
        onSubmit={(values) => {
          console.log("values ====>", values);
          console.log("placeId ====>", placeId);
          setFilterOptions({
            ...filterOptions,
            pageNo: 0,
            ...values,
            placeId,
            tz: selectedPlace?.timeZoneId,
          });
        }}
      >
        {(props) => (
          <form onSubmit={props.handleSubmit}>
            <FormControl fullWidth>
              <DateRangePicker
                id="duration"
                placeholder="Start Date - End Date"
                character=" - "
                showOneCalendar={false}
                size="lg"
                format="dd/MM/yyyy"
                ranges={[]}
                clearButton={true}
                onClean={() => {
                  console.log("clicked ====>2");
                  setFilterOptions({
                    status: "all",
                    placeId,
                    startDate: "",
                    endDate: "",
                    search: "",
                  });
                }}
                value={
                  props.values.startDate && props.values.endDate
                    ? [
                        new Date(props.values.startDate),
                        new Date(props.values.endDate),
                      ]
                    : undefined
                }
                onChange={(value) => {
                  if (value && value.length === 2) {
                    const [startDate, endDate] = value;
                    props.setFieldValue("startDate", moment(startDate));
                    props.setFieldValue("endDate", moment(endDate));
                  } else {
                    props.setFieldValue("startDate", null);
                    props.setFieldValue("endDate", null);
                  }
                }}
                onOk={props.handleSubmit}
              />
            </FormControl>
          </form>
        )}
      </Formik>
    </>
  );
};

export default TransactionFilterByDate;
