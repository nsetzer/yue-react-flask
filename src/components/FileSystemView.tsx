
import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom'
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';
import Button from 'material-ui/Button';

import Grid from 'material-ui/Grid';

import * as UiCard from 'material-ui/Card';
const Card = UiCard.default

import * as UiList  from 'material-ui/List';
const List = UiList.default
const ListItem = UiList.ListItem
const ListItemIcon = UiList.ListItemIcon
const ListItemText = UiList.ListItemText
const ListItemSecondaryAction = UiList.ListItemSecondaryAction
import IconButton from 'material-ui/IconButton';
import Send from 'material-ui-icons/Send';
import MoreVert from 'material-ui-icons/MoreVert';
import NavigateBefore from 'material-ui-icons/NavigateBefore';
import Menu, { MenuItem } from 'material-ui/Menu';

import * as filesystemActionCreators from '../actions/filesystem';
const actionCreators = Object.assign({},
                                     filesystemActionCreators);
import History from '../history'

import Typography from 'material-ui/Typography';

export interface IFileSystemViewProps {

}

export interface IFileSystemViewState {

}

class FileSystemView extends React.Component<IFileSystemViewProps, IFileSystemViewState> {

    constructor(props) {
        super(props);
        this.componentDidMount = this.componentDidMount.bind(this)
    }

    public componentDidMount() {
        return;
    }

    public render() {
        return (
            <div>
            Hello World
            </div>
        )
    }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators(actionCreators, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(FileSystemView);
