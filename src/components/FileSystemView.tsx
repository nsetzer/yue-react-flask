
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
    statusText: any,
    directories: any,
    files: any,
    name: string,
    parent_directory: string,
    current_directory: string,
    filesystemGetPath: (root,path) => any,
}

export interface IFileSystemViewState {

}

class FileSystemView extends React.Component<IFileSystemViewProps, IFileSystemViewState> {

    constructor(props) {
        super(props);
        // TODO: get current path from the route
        this.componentDidMount = this.componentDidMount.bind(this)
        this.openParentDirectory = this.openParentDirectory.bind(this)
        this.openDirectory = this.openDirectory.bind(this)
    }

    public componentDidMount() {

        this.props.filesystemGetPath("default", "");
        console.log("get file system root")
        return;

    }

    public openParentDirectory() {
        let path = this.props.parent_directory;
        console.log(path)
        this.props.filesystemGetPath("default", path);
    }

    public openDirectory(name) {
        let path = this.props.current_directory
        if (path) {
            path = path + "/" + name
        } else {
            path = name
        }
        console.log(path)
        this.props.filesystemGetPath("default", path);
    }

    public render() {
        return (
            <div>

            <h3>{this.props.name}:{this.props.current_directory}</h3>

            <List>

            <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={name}>
                <ListItem>
                    <ListItemText primary={".."}/>
                    <ListItemSecondaryAction>
                        <IconButton onClick={(e) => {this.openParentDirectory()}}>
                            <MoreVert />
                        </IconButton>
                    </ListItemSecondaryAction>
                </ListItem>
            </Card>

            {
              (this.props.directories && this.props.directories.length>0) ?
                this.props.directories.map( (name, index) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={name}>
                           <ListItem>
                             <ListItemText primary={name}/>
                             <ListItemSecondaryAction>
                               <IconButton onClick={(e) => {this.openDirectory(name)}}>
                                <MoreVert />
                               </IconButton>
                             </ListItemSecondaryAction>
                           </ListItem>
                         </Card>
                }) : null
            }

            {
              (this.props.files && this.props.files.length>0) ?
                this.props.files.map( (file, index) => {
                  return <Card style={{marginLeft:"8px",
                                       marginRight:"8px",
                                       marginTop:"5px",
                                       marginBottom:"5px"}}
                                key={file.name}>
                           <ListItem>
                             <ListItemText primary={file.name}
                                           secondary={file.size + " bytes"}/>
                             <ListItemSecondaryAction>
                               <IconButton onClick={(e) => {}}>
                                <MoreVert />
                               </IconButton>
                             </ListItemSecondaryAction>
                           </ListItem>
                         </Card>
                }) : null
            }

            </List>

            </div>
        )
    }
}

function mapStateToProps(state) {
    return {
        statusText: state.filesystem.statusText,
        directories: state.filesystem.directories,
        files: state.filesystem.files,
        name: state.filesystem.name,
        parent_directory: state.filesystem.parent_directory,
        current_directory: state.filesystem.current_directory,
    };
}

function mapDispatchToProps(dispatch) {
    return bindActionCreators(actionCreators, dispatch);
}

export default connect(
    mapStateToProps,
    mapDispatchToProps
)(FileSystemView);
