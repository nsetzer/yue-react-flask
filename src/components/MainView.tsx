import * as React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import { bindActionCreators } from 'redux';
import { connect } from 'react-redux';

import Button from 'material-ui/Button';

import Tabs, { Tab } from 'material-ui/Tabs';

import AppBar from 'material-ui/AppBar';

import Settings from 'material-ui-icons/Settings';
import ExitToApp from 'material-ui-icons/ExitToApp';
import LibraryMusic from 'material-ui-icons/LibraryMusic';
import * as ListIcons from 'material-ui-icons/List';
const ListIcon = ListIcons.default;

import { withTheme } from 'material-ui/styles';

import Divider from 'material-ui/Divider';
import * as UiList  from 'material-ui/List';
const List = UiList.default;
const ListItem = UiList.ListItem;
const ListItemIcon = UiList.ListItemIcon;
const ListItemText = UiList.ListItemText;

import SoundView from './player/SoundView';
import QueueView from './QueueView';
import DomainView from './DomainView';
import DomainArtistView from './DomainArtistView';
import DomainAlbumView from './DomainAlbumView';
import DomainGenreView from './DomainGenreView';
import SettingsView from './SettingsView';

import Paper from 'material-ui/Paper';

import Grid from 'material-ui/Grid';

import { Route, Redirect, Switch } from 'react-router-dom';

import History from '../history';

interface IDictionary<T> {
    [Key: string]: T;
}

import Drawer from 'material-ui/Drawer';

const drawerWidth = 260;
const headerHeight = 148; // no clue how to get this dynamically

const navStyles: IDictionary<React.CSSProperties> = {
  drawerPaper: {
    position: 'relative',
    height: '100%',
    width: drawerWidth,
  },
}

export interface IAppSideNavProps {
  permanent: boolean,
  open: boolean,
  onRequestClose: (event) => void
  onLogout: (event) => void
};

export interface IAppSideNavState {
}
class AppSideNav extends React.Component<IAppSideNavProps,IAppSideNavState> {
  constructor(props) {
    super(props);
    this.openPage = this.openPage.bind(this)
  }

  public openPage(url) {
    History.push(url);
    window.scrollTo(0, 0)
    this.props.onRequestClose(null);
  }

  public render() {
    return (
      <Drawer
      open={this.props.open}
      onRequestClose={this.props.onRequestClose}
      type={this.props.permanent?'permanent':'temporary'}

      anchor={'left'}>

      <div style={{width:drawerWidth}}>
      <div>
      <List>
        <ListItem />

        <ListItem button
                  onClick={() => {this.openPage('/main/queue')}}>
          <ListItemIcon>
            <ListIcon />
          </ListItemIcon>
          <ListItemText primary="Now Playing" />
        </ListItem>
        <ListItem button
                  onClick={() => {this.openPage('/main/library');}}>
          <ListItemIcon>
            <LibraryMusic />
          </ListItemIcon>
          <ListItemText primary="Library" />
        </ListItem>
        <ListItem button
                  onClick={() => {this.openPage('/main/genres');}}>
          <ListItemIcon>
            <LibraryMusic />
          </ListItemIcon>
          <ListItemText primary="Genres" />
        </ListItem>
        <ListItem button
                  onClick={() => {this.openPage('/main/settings');}}>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Settings" />
        </ListItem>
      <Divider />
        <ListItem button
                  onClick={this.props.onLogout}>
          <ListItemIcon>
            <ExitToApp />
          </ListItemIcon>
          <ListItemText primary="Logout" />
        </ListItem>
      </List>
      <Divider />
      <List>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 1" />
        </ListItem>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 2" />
        </ListItem>
        <ListItem button>
          <ListItemIcon>
            <Settings />
          </ListItemIcon>
          <ListItemText primary="Dummy 3" />
        </ListItem>
      </List>
  </div>
      </div>
      </Drawer>
    );
  }
}

export interface IMainViewProps {
  logoutAndRedirect: PropTypes.func;
  userName: PropTypes.string;
  theme: any;
}

export interface IMainViewState {
  open: boolean;
  currentTabIndex: number;
  screenWidth: number;
  screenHeight: number;
  headerHeight: number;
  pinNavBar: boolean;
  showNavBar: boolean;
  divElement: any;
}

const style: IDictionary<React.CSSProperties> = {
  header: {
    textAlign: 'center',
  },
  header_content: {
    padding: '5px',
    color: 'white'
  },
};

class MainView extends React.Component<IMainViewProps,IMainViewState> {

  public divElement = null

  constructor(props: any) {
    super(props);
    this.state = {open:true,
                  currentTabIndex: 0,
                  screenWidth: 0,
                  screenHeight: 0,
                  headerHeight: 0,
                  pinNavBar: true,
                  showNavBar: false,
                  divElement: null};
    this.divElement = null
    this.logout = this.logout.bind(this);
    this.onResize = this.onResize.bind(this);
    this.openNavBar = this.openNavBar.bind(this);

  }

  public logout(e) {
      e.preventDefault();
      this.props.logoutAndRedirect();
      this.setState({
          open: false,
      });
  }

  public componentDidMount() {
    this.onResize();
    window.addEventListener('resize', this.onResize);

    // const height = document.getElementById('AppHeader').clientHeight;
    const height = this.divElement.clientHeight;
    this.setState({headerHeight:height});
  }

  public componentDidUpdate() {

    // const height = document.getElementById('AppHeader').clientHeight;
    const height = this.divElement.clientHeight;
    console.log(height)
    // this.setState({headerHeight:height});
  }

  public componentWillUnmount() {
    window.removeEventListener('resize', this.onResize);
  }

  public onResize() {
    // https://material.io/guidelines/layout/responsive-ui.html#responsive-ui-breakpoints

    this.setState({screenWidth:window.innerWidth,
                   screenHeight: window.innerHeight,
                   pinNavBar: window.innerWidth > 960});
  }

  public openNavBar(open) {
    this.setState({showNavBar: open});
  }

  public render() {

    // get the default header height, or the computed height,
    // which ever is greater
    let _headerHeight = (this.divElement)?this.divElement.clientHeight:0
    _headerHeight = (_headerHeight>headerHeight)?_headerHeight:headerHeight

    let _drawerWidth = this.state.pinNavBar?drawerWidth:0;
    let navBar = <AppSideNav open={this.state.showNavBar}
                  permanent={this.state.pinNavBar}
                  onRequestClose={(e) => {this.openNavBar(false);}}
                  onLogout={(e) => {this.logout(e);}}
                  />;

    const { theme } = this.props;

    return (
      <div>

      <div id="AppHeader"
           ref={(divElement) => this.divElement = divElement}
           style={{ position: 'fixed',
                    width: 'calc(100% - ' + _drawerWidth + 'px)',
                    marginLeft: _drawerWidth,
                    background: theme.palette.primary['500'],
                    zIndex: 1000}} >
            <SoundView showMenuIcon={!this.state.pinNavBar}
                       openMenu={() => {this.openNavBar(true);}}
                       theme={theme}
                       />
      </div>

      { navBar }

      <Paper style={{ paddingTop: _headerHeight,
                      marginLeft: _drawerWidth}}>
          <Switch>
          <Route path={`/main/queue`} component={QueueView}/>
          <Route exact path={`/main/library`} component={DomainView}/>
          <Route exact path={`/main/genres`} component={DomainGenreView}/>
          <Route exact path={`/main/genres/view`} component={DomainView}/>
          <Route exact path={`/main/library/:artist`} component={DomainArtistView}/>
          <Route exact path={`/main/library/:artist/:album`} component={DomainAlbumView}/>
          <Route exact path={`/main/settings`} component={SettingsView}/>
          <Redirect from="/main" to="/main/queue" />
          {/*<Route path={'/main'} render={() => (
            <div>
            <h3>View Not Implemented</h3>
            <Button
              onClick={(e) => History.goBack()}
            >Go Back</Button>
            </div>
          )}/>*/}
          </Switch>
      </Paper>

      </div>
    )
  }
}

function mapStateToProps(state) {
  return {
    };
}

function mapDispatchToProps(dispatch) {
  return bindActionCreators({}, dispatch);
}

export default connect(
  mapStateToProps,
  mapDispatchToProps
)(withTheme()(MainView));
